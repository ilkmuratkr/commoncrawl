import asyncio
import logging
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.robots_crawler import RobotsCrawler
from config.settings import WORDPRESS_DOMAINS_FILE

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG seviyesine çıkardım
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Ana uygulama"""
    try:
        crawler = RobotsCrawler()
        await crawler.run()
        
        # Sonuç özeti
        print(f"\n💾 Sonuçlar: {crawler.wordpress_detector.output_file}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n❌ Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 