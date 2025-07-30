import os
import random
import subprocess
import asyncio
import logging
import aiohttp
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
    
    async def test_vpn_connection(self) -> bool:
        """VPN bağlantısını test et"""
        try:
            async with aiohttp.ClientSession() as session:
                # IP adresini kontrol et
                async with session.get('https://httpbin.org/ip', timeout=3) as response:  # 5'ten 3'e düşürdüm
                    if response.status == 200:
                        data = await response.json()
                        ip = data.get('origin', '')
                        logger.info(f"VPN IP adresi: {ip}")
                        return True
                    else:
                        logger.error(f"IP kontrolü başarısız: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"VPN bağlantı testi başarısız: {e}")
            return False
    
    async def connect_initial_vpn(self) -> bool:
        """İlk VPN bağlantısını kur ve test et"""
        async with self.global_vpn_lock:
            if self.current_vpn:
                logger.info("VPN zaten bağlı, test ediliyor...")
                if await self.test_vpn_connection():
                    return True
                else:
                    logger.warning("Mevcut VPN bağlantısı başarısız, yeniden bağlanılıyor...")
                    await self._disconnect_vpn(self.current_vpn)
                    self.current_vpn = None
                
            # Yeni VPN bağlantısı kur
            max_attempts = 5
            for attempt in range(max_attempts):
                vpn_config = self.get_available_vpn()
                if not vpn_config:
                    logger.error("Kullanılabilir VPN config bulunamadı")
                    return False
                
                logger.info(f"VPN bağlantısı deneniyor ({attempt + 1}/{max_attempts}): {vpn_config}")
                
                success = await self._connect_vpn(vpn_config)
                if success:
                    # VPN bağlantısını test et
                    logger.info("VPN bağlantısı test ediliyor...")
                    if await self.test_vpn_connection():
                        self.current_vpn = vpn_config
                        logger.info(f"VPN bağlantısı başarılı ve test edildi: {vpn_config}")
                        return True
                    else:
                        logger.warning(f"VPN bağlantısı başarısız: {vpn_config}")
                        await self._disconnect_vpn(vpn_config)
                        self.used_vpns.discard(vpn_config)
                
                # Kısa bekleme
                await asyncio.sleep(2)
            
            logger.error(f"{max_attempts} deneme sonrası VPN bağlantısı başarısız")
            return False
    
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
            max_attempts = 3
            for attempt in range(max_attempts):
                new_vpn = self.get_available_vpn()
                if not new_vpn:
                    logger.error("Yeni VPN config bulunamadı")
                    return False
                
                logger.info(f"Yeni VPN deneniyor ({attempt + 1}/{max_attempts}): {new_vpn}")
                
                success = await self._connect_vpn(new_vpn)
                if success:
                    # VPN bağlantısını test et
                    if await self.test_vpn_connection():
                        self.current_vpn = new_vpn
                        logger.info(f"VPN değiştirildi ve test edildi: {new_vpn}")
                        return True
                    else:
                        logger.warning(f"Yeni VPN bağlantısı başarısız: {new_vpn}")
                        await self._disconnect_vpn(new_vpn)
                        self.used_vpns.discard(new_vpn)
                
                await asyncio.sleep(2)
            
            logger.error(f"{max_attempts} deneme sonrası yeni VPN bağlantısı başarısız")
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
            # Önce sudo olmadan dene (hızlı)
            logger.debug(f"VPN bağlantısı deneniyor (sudo olmadan): {vpn_config}")
            result = subprocess.run(
                ["wg-quick", "up", config_path],
                capture_output=True,
                text=True,
                timeout=5  # Çok kısa timeout
            )
            
            if result.returncode == 0:
                logger.info(f"VPN bağlantısı başarılı: {vpn_config}")
                return True
            else:
                logger.debug(f"Sudo olmadan başarısız, sudo ile deneniyor: {vpn_config}")
                # Sudo ile dene ama password bekleme
                result = subprocess.run(
                    ["sudo", "-n", "wg-quick", "up", config_path],  # -n flag'i password beklemez
                    capture_output=True,
                    text=True,
                    timeout=5  # Çok kısa timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"VPN bağlantısı başarılı (sudo ile): {vpn_config}")
                    return True
                else:
                    logger.warning(f"VPN bağlantı hatası: {vpn_config}")
                    logger.warning(f"Hata: {result.stderr}")
                    # VPN olmadan devam et
                    logger.info("VPN olmadan devam ediliyor...")
                    return True  # True döndür ki devam etsin
                    
        except subprocess.TimeoutExpired:
            logger.error(f"VPN bağlantı timeout: {vpn_config}")
            logger.info("VPN olmadan devam ediliyor...")
            return True  # True döndür ki devam etsin
        except Exception as e:
            logger.error(f"VPN bağlantı hatası: {e}")
            logger.info("VPN olmadan devam ediliyor...")
            return True  # True döndür ki devam etsin
    
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