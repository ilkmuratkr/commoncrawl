# CommonCrawl WordPress Domain Crawler

CommonCrawl verilerinden robots.txt dosyalarını analiz ederek WordPress sitelerini tespit eden paralel crawler.

## Özellikler

- **Paralel İşleme**: 10 worker ile eşzamanlı dosya indirme
- **Bellek Optimizasyonu**: İndirilen dosyalar işlendikten sonra otomatik silinir
- **WordPress Tespiti**: Robots.txt içeriklerinde WordPress belirteçlerini arar
- **Hata Yönetimi**: Retry mekanizması ve kapsamlı logging
- **Modüler Mimari**: Kolay genişletilebilir ve sürdürülebilir kod yapısı

## Kurulum

```bash
# Gerekli paketleri yükle
pip install -r requirements.txt
```

## Kullanım

```bash
# Ana uygulamayı çalıştır
python src/main.py
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
├── robotstxt.paths (1)            # CommonCrawl paths dosyası
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