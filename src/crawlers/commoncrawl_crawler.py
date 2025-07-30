#!/usr/bin/env python3
"""
Common Crawl Crawler - VPN Entegrasyonu
403 hatası alındığında otomatik VPN rotasyonu ile çalışır
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.vpn_manager import VPNManager

logger = logging.getLogger(__name__)

class CommonCrawlCrawler:
    def __init__(self):
        self.vpn_manager = VPNManager()
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = 10
        self.retry_delay = 2
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Crawler'ı başlat"""
        logger.info("🚀 Common Crawl Crawler başlatılıyor...")
        
        # VPN bağlantısını kur
        success = await self.vpn_manager.connect_initial_vpn()
        if not success:
            logger.error("❌ VPN bağlantısı başarısız!")
            raise Exception("VPN bağlantısı kurulamadı")
        
        # HTTP session oluştur
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        logger.info("✅ Common Crawl Crawler başlatıldı")
    
    async def cleanup(self):
        """Crawler'ı temizle"""
        if self.session:
            await self.session.close()
        await self.vpn_manager.cleanup()
        logger.info("🧹 Common Crawl Crawler temizlendi")
    
    async def fetch_with_vpn_rotation(self, url: str, method: str = "GET", **kwargs) -> Optional[Dict[str, Any]]:
        """VPN rotasyonu ile veri çek"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"📡 İstek gönderiliyor ({attempt + 1}/{self.max_retries}): {url}")
                
                if method.upper() == "GET":
                    async with self.session.get(url, **kwargs) as response:
                        return await self._handle_response(response, url, attempt)
                elif method.upper() == "HEAD":
                    async with self.session.head(url, **kwargs) as response:
                        return await self._handle_response(response, url, attempt)
                else:
                    logger.error(f"❌ Desteklenmeyen HTTP metodu: {method}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ İstek hatası ({attempt + 1}/{self.max_retries}): {e}")
                await self._handle_error(attempt)
        
        logger.error(f"❌ {self.max_retries} deneme sonrası başarısız: {url}")
        return None
    
    async def _handle_response(self, response: aiohttp.ClientResponse, url: str, attempt: int) -> Optional[Dict[str, Any]]:
        """HTTP yanıtını işle"""
        status = response.status
        
        if status == 200:
            logger.info(f"✅ Başarılı yanıt: {url} (Status: {status})")
            try:
                # Gzip sıkıştırılmış dosyalar için binary okuma
                if 'gzip' in response.headers.get('content-encoding', '').lower() or url.endswith('.gz'):
                    content = await response.read()
                    import gzip
                    content = gzip.decompress(content).decode('utf-8')
                else:
                    content = await response.text()
                
                return {
                    "status": status,
                    "content": content,
                    "headers": dict(response.headers),
                    "url": url
                }
            except Exception as e:
                logger.error(f"❌ İçerik okuma hatası: {e}")
                return None
                
        elif status == 403:
            logger.warning(f"🚫 403 hatası alındı: {url}")
            logger.info("🔄 VPN rotasyonu başlatılıyor...")
            
            # VPN rotasyonu
            rotation_success = await self.vpn_manager.rotate_vpn_on_403()
            if rotation_success:
                logger.info(f"✅ VPN rotasyonu başarılı: {self.vpn_manager.current_vpn}")
                # Kısa bekleme
                await asyncio.sleep(self.retry_delay)
                return None  # Tekrar deneme için None döndür
            else:
                logger.error("❌ VPN rotasyonu başarısız!")
                return None
                
        elif status == 429:
            logger.warning(f"⏳ Rate limit (429): {url}")
            await asyncio.sleep(self.retry_delay * 2)
            return None
            
        elif status == 500:
            logger.warning(f"🔧 Sunucu hatası (500): {url}")
            await asyncio.sleep(self.retry_delay)
            return None
            
        else:
            logger.warning(f"⚠️ Beklenmeyen durum: {url} (Status: {status})")
            return None
    
    async def _handle_error(self, attempt: int):
        """Hata durumunda yapılacaklar"""
        if attempt < self.max_retries - 1:
            logger.info(f"⏳ {self.retry_delay} saniye bekleniyor...")
            await asyncio.sleep(self.retry_delay)
    
    async def fetch_commoncrawl_data(self, path: str) -> Optional[Dict[str, Any]]:
        """Common Crawl verilerini çek"""
        url = f"https://data.commoncrawl.org/{path}"
        return await self.fetch_with_vpn_rotation(url)
    
    async def fetch_commoncrawl_index(self, path: str) -> Optional[Dict[str, Any]]:
        """Common Crawl index dosyalarını çek"""
        url = f"https://data.commoncrawl.org/{path}"
        return await self.fetch_with_vpn_rotation(url, method="HEAD")

    async def run_with_vpn_rotation(self, wordpress_detector):
        """VPN rotasyonu ile crawler'ı çalıştır"""
        logger.info("🔄 VPN rotasyonu ile crawler başlatılıyor...")
        
        # İlk VPN bağlantısını kur
        success = await self.vpn_manager.connect_initial_vpn()
        if not success:
            logger.error("❌ İlk VPN bağlantısı başarısız!")
            return
        
        logger.info("✅ İlk VPN bağlantısı başarılı")
        
        # Senin robotstxt.paths dosyasını kullan
        try:
            logger.info("📥 robotstxt.paths (1) dosyası okunuyor...")
            
            # Dosyayı oku
            with open("robotstxt.paths (1)", "r") as f:
                content = f.read()
            
            if content:
                logger.info("✅ robotstxt.paths (1) dosyası okundu")
                
                # İlk 100 satırı işle (test için)
                lines = content.strip().split('\n')[:100]
                logger.info(f"📊 {len(lines)} satır işlenecek")
                
                processed_count = 0
                for line in lines:
                    if line.strip():
                        try:
                            logger.info(f"🔄 İşleniyor ({processed_count + 1}/{len(lines)}): {line}")
                            
                            # WARC dosyasını indir ve işle
                            await self.process_warc_file(line, wordpress_detector)
                            
                            processed_count += 1
                            
                        except Exception as e:
                            logger.error(f"❌ Satır işleme hatası: {e}")
                            continue
                
                logger.info(f"✅ İşlem tamamlandı! {processed_count} dosya işlendi")
                
            else:
                logger.error(f"❌ robotstxt.paths (1) dosyası okunamadı")
                
        except Exception as e:
            logger.error(f"❌ Crawler hatası: {e}", exc_info=True)
            raise

    async def process_warc_file(self, warc_path, wordpress_detector):
        """Robots.txt WARC dosyasını indir ve WordPress domain'leri tespit et"""
        try:
            # WARC dosyasını indir
            warc_url = f"https://data.commoncrawl.org/{warc_path}"
            logger.info(f"📥 Robots.txt WARC dosyası indiriliyor: {warc_url}")
            
            # WARC dosyaları için binary okuma
            result = await self.fetch_warc_file(warc_path)
            
            if result and result['status'] == 200:
                # Binary içeriği text'e çevir
                content = result['content']
                
                # Robots.txt içeriğinden WordPress domain'leri ara
                domains = wordpress_detector.extract_domains_from_robots_content(content)
                
                if domains:
                    # Bulunan domain'leri ekle
                    wordpress_detector.domain_manager.add_domains(domains)
                    for domain in domains:
                        logger.info(f"WordPress domain bulundu: {domain}")
                
                logger.info(f"✅ Robots.txt WARC dosyası işlendi: {warc_path}")
                
            elif result and result['status'] == 403:
                logger.warning(f"⚠️ 403 hatası: {warc_path}")
                # VPN rotasyonu zaten fetch_with_vpn_rotation'da yapılıyor
                
            else:
                logger.error(f"❌ WARC indirme hatası: {warc_path}")
                
        except Exception as e:
            logger.error(f"❌ WARC işleme hatası: {e}")
            raise

    async def fetch_warc_file(self, path: str) -> Optional[Dict[str, Any]]:
        """WARC dosyasını binary olarak indir"""
        url = f"https://data.commoncrawl.org/{path}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Binary içeriği oku
                        content = await response.read()
                        
                        # Gzip sıkıştırılmışsa aç
                        if path.endswith('.gz'):
                            import gzip
                            content = gzip.decompress(content)
                        
                        # Binary'den text'e çevir (hata toleranslı)
                        try:
                            text_content = content.decode('utf-8', errors='ignore')
                        except:
                            text_content = content.decode('latin-1', errors='ignore')
                        
                        return {
                            "status": response.status,
                            "content": text_content,
                            "headers": dict(response.headers),
                            "url": url
                        }
                    else:
                        logger.error(f"❌ WARC indirme hatası: {url} (Status: {response.status})")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ WARC fetch hatası: {e}")
            return None

# Test fonksiyonu
async def test_commoncrawl_crawler():
    """Common Crawl crawler'ını test et"""
    print("🧪 Common Crawl Crawler Testi")
    print("=" * 50)
    
    async with CommonCrawlCrawler() as crawler:
        # Ana sayfa testi
        print("1️⃣ Ana sayfa testi...")
        result = await crawler.fetch_commoncrawl_data("")
        if result:
            print(f"✅ Başarılı! Status: {result['status']}")
            print(f"📄 İçerik uzunluğu: {len(result['content'])} karakter")
        else:
            print("❌ Başarısız!")
        
        print()
        
        # Index dosyası testi
        print("2️⃣ Index dosyası testi...")
        result = await crawler.fetch_commoncrawl_index("crawl-data/CC-MAIN-2025-30/segments/1751905933612.63/robotstxt/CC-MAIN-20250707183638-20250707213638-00000.warc.gz")
        if result:
            print(f"✅ Başarılı! Status: {result['status']}")
        else:
            print("❌ Başarısız!")
    
    print()
    print("=" * 50)
    print("🏁 Test Tamamlandı!")

if __name__ == "__main__":
    asyncio.run(test_commoncrawl_crawler()) 