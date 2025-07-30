import os
import random
import subprocess
import asyncio
import logging
from typing import Optional, List
from config.settings import VPN_CONFIG_DIR, VPN_ROTATION_ON_403, VPN_CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)

class VPNManager:
    def __init__(self):
        self.vpn_configs = []
        self.current_vpn = None
        self.used_vpns = set()
        self.global_vpn_lock = asyncio.Lock()
        self._load_vpn_configs()
        
    def _load_vpn_configs(self):
        """VPN config dosyalarını yükle"""
        if not os.path.exists(VPN_CONFIG_DIR):
            logger.warning(f"VPN config dizini bulunamadı: {VPN_CONFIG_DIR}")
            return
            
        for file in os.listdir(VPN_CONFIG_DIR):
            if file.endswith('.conf'):
                self.vpn_configs.append(file)
        
        logger.info(f"{len(self.vpn_configs)} VPN config dosyası yüklendi")
    
    def get_available_vpn(self) -> Optional[str]:
        """Kullanılabilir bir VPN config seç"""
        available = [vpn for vpn in self.vpn_configs if vpn not in self.used_vpns]
        
        if not available:
            # Tüm VPN'ler kullanıldıysa, used_vpns'i temizle
            self.used_vpns.clear()
            available = self.vpn_configs
            logger.info("Tüm VPN'ler kullanıldı, liste sıfırlandı")
        
        if available:
            vpn = random.choice(available)
            self.used_vpns.add(vpn)
            return vpn
        
        return None
    
    async def connect_initial_vpn(self) -> bool:
        """İlk VPN bağlantısını kur"""
        async with self.global_vpn_lock:
            if self.current_vpn:
                logger.info("VPN zaten bağlı, yeni bağlantı kurulmuyor")
                return True
                
            vpn_config = self.get_available_vpn()
            if not vpn_config:
                logger.error("Kullanılabilir VPN config bulunamadı")
                return False
            
            success = await self._connect_vpn(vpn_config)
            if success:
                self.current_vpn = vpn_config
                logger.info(f"İlk VPN bağlantısı kuruldu: {vpn_config}")
            return success
    
    async def rotate_vpn_on_403(self) -> bool:
        """403 hatası alınca VPN değiştir"""
        if not VPN_ROTATION_ON_403:
            logger.info("VPN rotasyon devre dışı")
            return False
            
        async with self.global_vpn_lock:
            # Mevcut VPN'i kes
            if self.current_vpn:
                await self._disconnect_vpn(self.current_vpn)
                logger.info(f"Mevcut VPN kesildi: {self.current_vpn}")
            
            # Yeni VPN seç ve bağlan
            new_vpn = self.get_available_vpn()
            if not new_vpn:
                logger.error("Yeni VPN config bulunamadı")
                return False
            
            success = await self._connect_vpn(new_vpn)
            if success:
                self.current_vpn = new_vpn
                logger.info(f"VPN değiştirildi: {new_vpn}")
                return True
            else:
                logger.error(f"Yeni VPN bağlantısı başarısız: {new_vpn}")
                return False
    
    async def _connect_vpn(self, vpn_config: str) -> bool:
        """VPN bağlantısı kur"""
        config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
        
        if not os.path.exists(config_path):
            logger.error(f"VPN config dosyası bulunamadı: {config_path}")
            return False
        
        # Dosya izinlerini düzelt
        try:
            os.chmod(config_path, 0o600)
        except Exception as e:
            logger.warning(f"Dosya izinleri düzeltilemedi: {e}")
        
        try:
            # Önce sudo olmadan dene
            result = subprocess.run(
                ["wg-quick", "up", config_path],
                capture_output=True,
                text=True,
                timeout=VPN_CONNECTION_TIMEOUT
            )
            
            if result.returncode == 0:
                logger.info(f"VPN bağlantısı başarılı: {vpn_config}")
                return True
            else:
                # Sudo ile dene
                result = subprocess.run(
                    ["sudo", "wg-quick", "up", config_path],
                    capture_output=True,
                    text=True,
                    timeout=VPN_CONNECTION_TIMEOUT
                )
                
                if result.returncode == 0:
                    logger.info(f"VPN bağlantısı başarılı (sudo ile): {vpn_config}")
                    return True
                else:
                    logger.warning(f"VPN bağlantı hatası: {vpn_config}")
                    logger.warning(f"Hata: {result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            logger.error(f"VPN bağlantı timeout: {vpn_config}")
            return False
        except Exception as e:
            logger.error(f"VPN bağlantı hatası: {e}")
            return False
    
    async def _disconnect_vpn(self, vpn_config: str) -> bool:
        """VPN bağlantısını kes"""
        config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
        
        try:
            # Önce wg-quick down ile dene
            result = subprocess.run(
                ["wg-quick", "down", config_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Sudo ile dene
                result = subprocess.run(
                    ["sudo", "wg-quick", "down", config_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            # Interface adını çıkar (uzantısız)
            interface_name = vpn_config.replace('.conf', '')
            
            # Manuel olarak interface'i sil
            try:
                subprocess.run(
                    ["sudo", "ip", "link", "delete", "dev", interface_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            except:
                pass  # Interface zaten silinmiş olabilir
                
            logger.info(f"VPN bağlantısı kesildi: {vpn_config}")
            return True
            
        except Exception as e:
            logger.warning(f"VPN kesme hatası: {e}")
            return True  # Hata olsa bile True döndür (devam et)
    
    async def disconnect_current_vpn(self) -> bool:
        """Mevcut VPN bağlantısını kes"""
        if self.current_vpn:
            success = await self._disconnect_vpn(self.current_vpn)
            self.current_vpn = None
            return success
        return True
    
    async def cleanup(self):
        """Tüm VPN bağlantılarını temizle"""
        await self.disconnect_current_vpn()
        logger.info("VPN Manager temizlendi") 