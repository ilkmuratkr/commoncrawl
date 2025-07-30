import asyncio
import logging
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.robots_crawler import RobotsCrawler
from config.settings import WORDPRESS_DOMAINS_FILE

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Ana uygulama"""
    try:
        logger.info("WordPress Domain Crawler başlatılıyor...")
        
        # Crawler'ı başlat
        crawler = RobotsCrawler()
        
        # İşlemi çalıştır
        await crawler.run()
        
        # Sonuçları göster
        if WORDPRESS_DOMAINS_FILE.exists():
            with open(WORDPRESS_DOMAINS_FILE, 'r', encoding='utf-8') as f:
                domains = f.read().splitlines()
            
            logger.info(f"İşlem tamamlandı! {len(domains)} WordPress domain'i bulundu")
            logger.info(f"Sonuçlar: {WORDPRESS_DOMAINS_FILE}")
            
            # İlk 10 domain'i göster
            if domains:
                logger.info("İlk 10 domain:")
                for i, domain in enumerate(domains[:10]):
                    logger.info(f"  {i+1}. {domain}")
        else:
            logger.warning("Sonuç dosyası bulunamadı!")
            
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"Uygulama hatası: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 