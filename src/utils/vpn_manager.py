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
        
    async def cleanup_existing_interfaces(self):
        """Mevcut WireGuard interface'lerini temizle"""
        try:
            logger.info("Mevcut WireGuard interface'leri temizleniyor...")
            
            # macOS için ifconfig kullan
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    'ifconfig', '-l',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=5.0
            )
            
            if result.returncode == 0:
                stdout, _ = await result.communicate()
                interfaces = stdout.decode().strip().split()
                
                # WireGuard interface'lerini bul (utun*)
                for interface in interfaces:
                    if interface.startswith('utun') and interface != 'utun0':
                        logger.info(f"Interface temizleniyor: {interface}")
                        try:
                            # Interface'i kapat
                            await asyncio.wait_for(
                                asyncio.create_subprocess_exec(
                                    'sudo', 'ifconfig', interface, 'down',
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE
                                ),
                                timeout=5.0
                            )
                            logger.info(f"✅ Interface kapatıldı: {interface}")
                        except Exception as e:
                            logger.debug(f"Interface kapatma hatası (normal): {e}")
            
            logger.info("Interface temizleme tamamlandı")
            
        except Exception as e:
            logger.error(f"Interface temizleme hatası: {e}")
    
    def _load_vpn_configs(self):
        """VPN config dosyalarını yükle"""
        if not os.path.exists(VPN_CONFIG_DIR):
            logger.warning(f"VPN config dizini bulunamadı: {VPN_CONFIG_DIR}")
            return []
            
        for file in os.listdir(VPN_CONFIG_DIR):
            if file.endswith('.conf') and not file.endswith('_split.conf') and not '_split' in file:
                self.vpn_configs.append(file)
        
        logger.info(f"{len(self.vpn_configs)} VPN config dosyası yüklendi")
        return self.vpn_configs
    
    def get_available_vpn(self) -> Optional[str]:
        """Kullanılabilir bir VPN config seç - geliştirilmiş rotasyon"""
        available = [vpn for vpn in self.vpn_configs if vpn not in self.used_vpns]
        
        if not available:
            # Tüm VPN'ler kullanıldıysa, used_vpns'i temizle
            self.used_vpns.clear()
            available = self.vpn_configs
            logger.info("🔄 Tüm VPN'ler kullanıldı, liste sıfırlandı")
            logger.info(f"📊 Toplam VPN sayısı: {len(self.vpn_configs)}")
        
        if available:
            vpn = random.choice(available)
            self.used_vpns.add(vpn)
            logger.info(f"🔗 VPN seçildi: {vpn} (Kullanılan: {len(self.used_vpns)}/{len(self.vpn_configs)})")
            return vpn
        
        logger.error("❌ Kullanılabilir VPN bulunamadı!")
        return None
    
    async def test_vpn_connection(self) -> bool:
        """VPN bağlantısını test et - IP değişikliğini kontrol et"""
        try:
            logger.info("VPN bağlantısı test ediliyor...")
            
            # Birden fazla IP servisi dene
            ip_services = [
                'https://httpbin.org/ip',
                'https://api.ipify.org?format=json',
                'https://ipinfo.io/json',
                'https://api.myip.com'
            ]
            
            for service in ip_services:
                try:
                    timeout = aiohttp.ClientTimeout(total=5)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(service) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                if service == 'https://httpbin.org/ip':
                                    current_ip = data.get('origin', '')
                                elif service == 'https://api.ipify.org?format=json':
                                    current_ip = data.get('ip', '')
                                elif service == 'https://ipinfo.io/json':
                                    current_ip = data.get('ip', '')
                                elif service == 'https://api.myip.com':
                                    current_ip = data.get('ip', '')
                                else:
                                    continue
                                
                                logger.info(f"VPN Test - Mevcut IP: {current_ip}")
                                
                                # Sunucunun orijinal IP'si ile karşılaştır
                                if current_ip != "35.225.81.214":
                                    logger.info(f"✅ VPN bağlantısı başarılı - IP değişti: {current_ip}")
                                    return True
                                else:
                                    logger.warning(f"❌ VPN bağlantısı başarısız - IP değişmedi: {current_ip}")
                                    return False
                                    
                except Exception as e:
                    logger.debug(f"IP servisi başarısız {service}: {e}")
                    continue
            
            logger.error("❌ Tüm IP servisleri başarısız")
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
        """403 hatası alınca VPN değiştir - daha agresif rotasyon"""
        if not VPN_ROTATION_ON_403:
            logger.info("VPN rotasyon devre dışı")
            return False
            
        async with self.global_vpn_lock:
            # Mevcut VPN'i kes
            if self.current_vpn:
                await self._disconnect_vpn(self.current_vpn)
                logger.info(f"403 hatası nedeniyle VPN değiştiriliyor: {self.current_vpn}")
            
            # Daha fazla VPN dene
            max_attempts = 10  # 3'ten 10'a çıkarıldı
            successful_vpns = []
            
            for attempt in range(max_attempts):
                new_vpn = self.get_available_vpn()
                if not new_vpn:
                    logger.error("Yeni VPN config bulunamadı")
                    return False
                
                logger.info(f"403 rotasyon - Yeni VPN deneniyor ({attempt + 1}/{max_attempts}): {new_vpn}")
                
                success = await self._connect_vpn(new_vpn)
                if success:
                    # VPN bağlantısını test et
                    if await self.test_vpn_connection():
                        self.current_vpn = new_vpn
                        successful_vpns.append(new_vpn)
                        logger.info(f"✅ 403 rotasyon başarılı - VPN değiştirildi: {new_vpn}")
                        return True
                    else:
                        logger.warning(f"Yeni VPN bağlantısı başarısız: {new_vpn}")
                        await self._disconnect_vpn(new_vpn)
                        self.used_vpns.discard(new_vpn)
                else:
                    logger.warning(f"VPN bağlantısı başarısız: {new_vpn}")
                    self.used_vpns.discard(new_vpn)
                
                # Kısa bekleme
                await asyncio.sleep(1)
            
            logger.error(f"{max_attempts} deneme sonrası 403 rotasyon başarısız")
            logger.info(f"Başarılı VPN'ler: {successful_vpns}")
            return False
    
    async def _connect_vpn(self, vpn_config: str) -> bool:
        """VPN'e bağlan ve test et"""
        try:
            config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
            
            # Dosya izinlerini ayarla
            os.chmod(config_path, 0o600)
            
            # Interface adını çıkar
            interface_name = self._extract_interface_name(vpn_config)
            if not interface_name:
                return False
            
            # Interface zaten mevcut mu kontrol et
            check_result = await asyncio.create_subprocess_exec(
                'ip', 'link', 'show', interface_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await check_result.communicate()
            
            if check_result.returncode == 0:
                logger.info(f"✅ VPN interface zaten mevcut: {interface_name}")
                self.current_vpn = vpn_config
                return True
            
            # Split tunneling config oluştur
            split_config_path = self._setup_split_tunneling(vpn_config)
            
            logger.info(f"Split tunneling VPN bağlantısı deneniyor: {vpn_config}")
            
            # Sudo ile bağlan
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
                self.current_vpn = vpn_config
                return True
            else:
                stdout, stderr = await result.communicate()
                stderr_text = stderr.decode()
                
                # Interface zaten mevcut hatası
                if "already exists" in stderr_text:
                    logger.info(f"✅ VPN interface zaten mevcut: {vpn_config}")
                    self.current_vpn = vpn_config
                    return True
                
                # Route zaten mevcut hatası
                if "File exists" in stderr_text:
                    logger.info(f"✅ VPN route'ları zaten mevcut: {vpn_config}")
                    self.current_vpn = vpn_config
                    return True
                
                logger.error(f"❌ VPN bağlantısı başarısız: {vpn_config}")
                logger.error(f"stdout: {stdout.decode()}")
                logger.error(f"stderr: {stderr_text}")
                return False
            
        except Exception as e:
            logger.error(f"VPN bağlantı hatası: {e}")
            return False
    
    async def _disconnect_vpn(self, vpn_config: str) -> bool:
        """VPN bağlantısını kes"""
        try:
            # Split tunneling config dosyasını kullan
            base_name = vpn_config.replace('.conf', '')
            # Interface adını config dosyası adından çıkar
            interface_name = f"wg{base_name[-3:]}"
            split_config_path = os.path.join(VPN_CONFIG_DIR, f"{interface_name}.conf")
            
            # Önce wg-quick down ile dene
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    'wg-quick', 'down', split_config_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=10.0
            )
            
            if result.returncode != 0:
                # Sudo ile dene
                result = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        'sudo', 'wg-quick', 'down', split_config_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    ),
                    timeout=10.0
                )
            
            # Manuel olarak interface'i sil
            try:
                await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        'sudo', 'ip', 'link', 'delete', 'dev', interface_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    ),
                    timeout=5.0
                )
            except Exception as e:
                logger.debug(f"Interface silme hatası (normal): {e}")
            
            # Split config dosyasını sil
            try:
                if os.path.exists(split_config_path):
                    os.remove(split_config_path)
                    logger.debug(f"Split config dosyası silindi: {split_config_path}")
            except Exception as e:
                logger.debug(f"Split config silme hatası: {e}")
            
            logger.info(f"VPN bağlantısı kesildi: {vpn_config}")
            return True
            
        except Exception as e:
            logger.error(f"VPN bağlantısı kesme hatası: {e}")
            return False
    
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

    def _extract_interface_name(self, vpn_config: str) -> str:
        """VPN config dosyasından interface adını çıkar"""
        try:
            # Config dosyasını oku
            config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Interface adını bul
            for line in content.split('\n'):
                if line.strip().startswith('Name = '):
                    return line.split('=')[1].strip()
            
            # Eğer Name bulunamazsa, dosya adından çıkar
            base_name = vpn_config.replace('.conf', '')
            return f"wg{base_name[-3:]}"
            
        except Exception as e:
            logger.error(f"Interface adı çıkarma hatası: {e}")
            return None

    def _setup_split_tunneling(self, vpn_config: str) -> str:
        """Split tunneling için VPN config'i düzenle - sadece CommonCrawl IP'leri"""
        config_path = os.path.join(VPN_CONFIG_DIR, vpn_config)
        
        try:
            # Config dosyasını oku
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # CommonCrawl'ın gerçek IP adresleri (sadece bunlar için VPN kullan)
            commoncrawl_ips = [
                # data.commoncrawl.org IP'leri (güncel)
                "3.160.57.128/32",   # data.commoncrawl.org IP
                "3.160.57.34/32",    # data.commoncrawl.org IP
                "3.160.57.125/32",   # data.commoncrawl.org IP
                "3.160.57.65/32",    # data.commoncrawl.org IP
                # CloudFront IP range'leri (yedek)
                "3.160.0.0/16",      # CloudFront IP range
                # Test siteleri IP'leri
                "54.221.61.107/32",  # httpbin.org IP
                "34.192.139.201/32", # httpbin.org IP
                "52.86.149.41/32",   # httpbin.org IP
                "34.197.172.56/32",  # httpbin.org IP
                "104.26.13.205/32",  # api.ipify.org IP
                "172.67.74.152/32",  # api.ipify.org IP
                "104.26.12.205/32",  # api.ipify.org IP
                # IP test siteleri
                "34.195.196.24/32",  # ipinfo.io
                "104.18.2.5/32",     # ipinfo.io (alternatif)
                "104.18.3.5/32",     # ipinfo.io (alternatif)
            ]
            
            # AllowedIPs satırını bul ve değiştir, DNS'i kaldır
            lines = config_content.split('\n')
            new_lines = []
            
            for line in lines:
                if line.startswith('AllowedIPs = '):
                    # Sadece CommonCrawl IP'lerini ekle
                    new_line = f"AllowedIPs = {', '.join(commoncrawl_ips)}"
                    new_lines.append(new_line)
                elif line.startswith('DNS = '):
                    # DNS satırını kaldır
                    continue
                else:
                    new_lines.append(line)
            
            # Benzersiz interface adı oluştur (config dosyası adından)
            base_name = vpn_config.replace('.conf', '')
            # Sadece son 3 karakteri al ve wg ile başlat
            interface_name = f"wg{base_name[-3:]}"
            temp_config_path = os.path.join(VPN_CONFIG_DIR, f"{interface_name}.conf")
            
            with open(temp_config_path, 'w') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"Split tunneling config oluşturuldu: {temp_config_path}")
            logger.info(f"Benzersiz interface adı: {interface_name}")
            logger.info(f"CommonCrawl IP'leri eklendi: {len(commoncrawl_ips)} adet")
            logger.info(f"IP'ler: {', '.join(commoncrawl_ips)}")
            return temp_config_path
            
        except Exception as e:
            logger.error(f"Split tunneling config hatası: {e}")
            return config_path  # Orijinal config'i kullan 