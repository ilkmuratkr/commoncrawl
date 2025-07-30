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
            return []
            
        for file in os.listdir(VPN_CONFIG_DIR):
            if file.endswith('.conf'):
                self.vpn_configs.append(file)
        
        logger.info(f"{len(self.vpn_configs)} VPN config dosyası yüklendi")
        return self.vpn_configs
    
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
        """VPN bağlantısını test et - gerçek IP'yi kontrol et"""
        try:
            logger.info("VPN bağlantısı test ediliyor...")
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('https://httpbin.org/ip') as response:
                    if response.status == 200:
                        data = await response.json()
                        current_ip = data.get('origin', '')
                        logger.info(f"VPN Test - Mevcut IP: {current_ip}")
                        
                        # Sunucunun orijinal IP'si ile karşılaştır
                        if current_ip != "35.225.81.214":
                            logger.info(f"✅ VPN bağlantısı başarılı - IP değişti: {current_ip}")
                            return True
                        else:
                            logger.warning(f"❌ VPN bağlantısı başarısız - IP değişmedi: {current_ip}")
                            return False
                    else:
                        logger.error(f"VPN test hatası - HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"VPN test hatası: {e}")
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
        """VPN'e bağlan ve test et"""
        try:
            config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
            
            # Dosya izinlerini ayarla
            os.chmod(config_path, 0o600)
            
            # Split tunneling config oluştur
            split_config_path = self._setup_split_tunneling(vpn_config)
            
            logger.info(f"Split tunneling VPN bağlantısı deneniyor: {vpn_config}")
            
            # Önce sudo olmadan dene
            try:
                result = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        'wg-quick', 'up', split_config_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    ),
                    timeout=5.0
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ VPN bağlantısı başarılı (sudo olmadan): {vpn_config}")
                else:
                    logger.warning(f"VPN bağlantısı başarısız (sudo olmadan), sudo ile deneniyor...")
                    raise Exception("sudo gerekli")
                    
            except (asyncio.TimeoutError, Exception) as e:
                logger.info(f"sudo ile VPN bağlantısı deneniyor: {vpn_config}")
                
                # sudo ile dene
                result = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        'sudo', 'wg-quick', 'up', split_config_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    ),
                    timeout=VPN_CONNECTION_TIMEOUT
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ Split tunneling VPN bağlantısı başarılı: {vpn_config}")
                else:
                    stdout, stderr = await result.communicate()
                    logger.error(f"❌ VPN bağlantısı başarısız: {vpn_config}")
                    logger.error(f"stdout: {stdout.decode()}")
                    logger.error(f"stderr: {stderr.decode()}")
                    return False
            
            # VPN bağlantısını test et
            await asyncio.sleep(2)  # Bağlantının kurulması için bekle
            test_result = await self.test_vpn_connection()
            
            if test_result:
                self.current_vpn = vpn_config
                logger.info(f"✅ VPN bağlantısı ve test başarılı: {vpn_config}")
                return True
            else:
                logger.error(f"❌ VPN bağlantısı başarısız - test geçemedi: {vpn_config}")
                # Bağlantıyı kapat
                await self._disconnect_vpn(vpn_config)
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

    def _setup_split_tunneling(self, vpn_config: str) -> str:
        """Split tunneling için VPN config'i düzenle - sadece CommonCrawl IP'leri"""
        config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
        
        try:
            # Config dosyasını oku
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # CommonCrawl'ın gerçek IP adresleri (sadece bunlar için VPN kullan)
            commoncrawl_ips = [
                # data.commoncrawl.org IP'leri
                "3.169.85.122/32",   # data.commoncrawl.org IP
                "3.169.85.39/32",    # data.commoncrawl.org IP
                "3.169.85.59/32",    # data.commoncrawl.org IP
                "3.169.85.63/32",    # data.commoncrawl.org IP
                # CloudFront IP range'leri (yedek)
                "3.169.0.0/16",      # CloudFront IP range
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
            
            # Düzenlenmiş config'i geçici dosyaya yaz (çift split olmasın)
            base_name = vpn_config.replace('.conf', '')
            temp_config_path = os.path.join(VPN_CONFIG_DIR, f"{base_name}_split.conf")
            with open(temp_config_path, 'w') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"Split tunneling config oluşturuldu: {temp_config_path}")
            logger.info(f"CommonCrawl IP'leri eklendi: {len(commoncrawl_ips)} adet")
            logger.info(f"IP'ler: {', '.join(commoncrawl_ips)}")
            return temp_config_path
            
        except Exception as e:
            logger.error(f"Split tunneling config hatası: {e}")
            return config_path  # Orijinal config'i kullan 