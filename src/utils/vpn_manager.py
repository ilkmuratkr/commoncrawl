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
                async with session.get('https://httpbin.org/ip', timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        ip = data.get('origin', '')
                        logger.info(f"VPN IP adresi: {ip}")
                        
                        # IP adresini kontrol et - VPN IP'si mi?
                        if ip and not ip.startswith('35.225.81.214'):  # Sunucu IP'si değilse VPN çalışıyor
                            logger.info(f"VPN bağlantısı başarılı - IP: {ip}")
                            return True
                        else:
                            logger.warning(f"VPN bağlantısı başarısız - Hala sunucu IP'si: {ip}")
                            return False
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
        """VPN bağlantısı kur (normal bağlantı)"""
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
            logger.debug(f"VPN bağlantısı deneniyor (sudo olmadan): {vpn_config}")
            result = subprocess.run(
                ["wg-quick", "up", config_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info(f"VPN bağlantısı başarılı: {vpn_config}")
                return True
            else:
                # Sudo ile dene - password soracak
                logger.info(f"VPN bağlantısı için sudo password gerekli: {vpn_config}")
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
                    logger.error(f"VPN bağlantı hatası: {vpn_config}")
                    logger.error(f"Hata: {result.stderr}")
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

    def _setup_split_tunneling(self, vpn_config: str) -> bool:
        """Split tunneling için VPN config'i düzenle"""
        config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
        
        try:
            # Config dosyasını oku
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Split tunneling için AllowedIPs'i düzenle
            # Sadece CommonCrawl IP'lerini ekle
            commoncrawl_ips = [
                "52.84.0.0/15",  # CloudFront IP range
                "13.32.0.0/15",  # CloudFront IP range
                "13.35.0.0/16",  # CloudFront IP range
            ]
            
            # AllowedIPs satırını bul ve değiştir
            lines = config_content.split('\n')
            new_lines = []
            
            for line in lines:
                if line.startswith('AllowedIPs = '):
                    # Sadece CommonCrawl IP'lerini ekle
                    new_line = f"AllowedIPs = {', '.join(commoncrawl_ips)}"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            
            # Düzenlenmiş config'i geçici dosyaya yaz
            temp_config_path = config_path.replace('.conf', '_split.conf')
            with open(temp_config_path, 'w') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"Split tunneling config oluşturuldu: {temp_config_path}")
            return temp_config_path
            
        except Exception as e:
            logger.error(f"Split tunneling config hatası: {e}")
            return config_path  # Orijinal config'i kullan 