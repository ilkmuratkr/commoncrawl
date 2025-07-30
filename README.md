# CommonCrawl WordPress Domain Crawler

CommonCrawl verilerinden robots.txt dosyalarını analiz ederek WordPress sitelerini tespit eden paralel crawler.

## Özellikler

- **Paralel İşleme**: 10 worker ile eşzamanlı dosya indirme
- **Bellek Optimizasyonu**: İndirilen dosyalar işlendikten sonra otomatik silinir
- **WordPress Tespiti**: Robots.txt içeriklerinde WordPress belirteçlerini arar
- **Hata Yönetimi**: Retry mekanizması ve kapsamlı logging
- **Modüler Mimari**: Kolay genişletilebilir ve sürdürülebilir kod yapısı

## GitHub'dan Kurulum

```bash
# Repository'yi klonla
git clone https://github.com/ilkmuratkr/commoncrawl.git
cd commoncrawl

# Gerekli paketleri yükle
pip install -r requirements.txt
```

## Kullanım

```bash
# Ana uygulamayı çalıştır
python3 src/main.py

# Veya çalıştırma scriptini kullan
python3 run_crawler.py
```

## Proje Yapısı

```
commoncrawl/
├── src/
│   ├── crawlers/
│   │   └── robots_crawler.py      # Ana crawler sınıfı
│   ├── processors/
│   │   └── wordpress_detector.py  # WordPress tespit işlemleri
│   ├── utils/
│   │   └── file_downloader.py     # Dosya indirme işlemleri
│   └── main.py                    # Ana uygulama
├── config/
│   └── settings.py                # Proje ayarları
├── data/
│   ├── raw/                       # Ham veriler
│   ├── processed/                  # İşlenmiş veriler
│   └── results/                   # Sonuçlar
├── robotstxt.paths (1)            # CommonCrawl paths dosyası (100,000+ URL)
├── run_crawler.py                 # Çalıştırma scripti
└── requirements.txt
```

## Ayarlar

`config/settings.py` dosyasından aşağıdaki ayarları değiştirebilirsiniz:

- `MAX_WORKERS`: Paralel worker sayısı (varsayılan: 10)
- `CHUNK_SIZE`: Her worker'ın işleyeceği path sayısı (varsayılan: 1000)
- `BATCH_SIZE`: Her seferde indirilecek dosya sayısı (varsayılan: 100)
- `REQUEST_TIMEOUT`: HTTP timeout süresi (varsayılan: 30 saniye)

## WordPress Belirteçleri

Aşağıdaki belirteçler robots.txt dosyalarında aranır:

- `wp-`
- `wp-content`
- `wp-includes`
- `wp-admin`
- `wordpress`

## Çıktı

Sonuçlar `data/results/wordpress_domains.txt` dosyasında saklanır. Her satırda bir domain bulunur.

## Loglar

Uygulama çalışırken detaylı loglar `crawler.log` dosyasına yazılır.

## Performans

- **Hız**: 10 worker ile paralel işleme
- **Bellek**: İndirilen dosyalar otomatik temizlenir
- **Doğruluk**: Robots.txt içeriklerinde WordPress belirteçleri aranır

## Test Sonuçları

- **10 dosyadan 353 WordPress domain'i** bulundu
- **0 tekrar** - Sistem otomatik tekrar kontrolü yapıyor
- **Hızlı işleme** - 5 saniyede 10 dosya tamamlandı

## Katkıda Bulunma

1. Repository'yi fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun 