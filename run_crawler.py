#!/usr/bin/env python3
"""
CommonCrawl WordPress Domain Crawler - VPN Entegrasyonu
403 hatası alındığında otomatik VPN rotasyonu ile çalışır
"""

import asyncio
import sys
import logging
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawlers.commoncrawl_crawler import CommonCrawlCrawler
from src.processors.wordpress_detector import WordPressDetector
from config.settings import WORDPRESS_DOMAINS_FILE

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_vpn.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Ana uygulama - VPN entegrasyonu ile"""
    print("🚀 CommonCrawl WordPress Domain Crawler - VPN Entegrasyonu")
    print("🔐 552 VPN sunucusu ile 403 rotasyonu aktif")
    print("📊 100,000 robots.txt dosyası işlenecek")
    print("⚡ 10 paralel worker ile çalışacak")
    print("💾 Sonuçlar: data/results/wordpress_domains.txt")
    print("=" * 60)
    
    try:
        # VPN entegrasyonu ile crawler başlat
        async with CommonCrawlCrawler() as crawler:
            # WordPress detector'ı başlat
            wordpress_detector = WordPressDetector(WORDPRESS_DOMAINS_FILE)
            
            # Crawler'ı çalıştır
            await crawler.run_with_vpn_rotation(wordpress_detector)
            
            # Sonuç özeti
            print(f"\n💾 Sonuçlar: {wordpress_detector.output_file}")
            print(f"📊 Bulunan WordPress domain sayısı: {wordpress_detector.get_domain_count()}")
            
    except KeyboardInterrupt:
        print("\n⏹️ Kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        logger.error(f"Ana uygulama hatası: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 