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