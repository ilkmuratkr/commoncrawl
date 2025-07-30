#!/usr/bin/env python3
"""
CommonCrawl WordPress Domain Crawler
Tam ölçekli çalıştırma scripti
"""

import asyncio
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.main import main

if __name__ == "__main__":
    print("🚀 CommonCrawl WordPress Domain Crawler başlatılıyor...")
    print("📊 100,000 robots.txt dosyası işlenecek")
    print("⚡ 10 paralel worker ile çalışacak")
    print("💾 Sonuçlar: data/results/wordpress_domains.txt")
    print("=" * 60)
    
    try:
        asyncio.run(main())
        print("\n✅ İşlem başarıyla tamamlandı!")
    except KeyboardInterrupt:
        print("\n⏹️ Kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        sys.exit(1) 