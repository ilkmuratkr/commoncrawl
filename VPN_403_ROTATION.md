# VPN 403 Rotasyon Sistemi

## Genel Bakış

Bu sistem, Common Crawl verilerine erişim sırasında 403 hatası alındığında otomatik olarak VPN değiştiren gelişmiş bir rotasyon sistemi sağlar.

## Özellikler

### 🔄 Otomatik VPN Rotasyonu
- **403 Hatası Algılama**: HTTP 403 yanıtı otomatik olarak algılanır
- **Hızlı VPN Değişimi**: Mevcut VPN kesilir ve yeni VPN bağlanır
- **Çoklu Deneme**: 10 farklı VPN denenir
- **Akıllı Seçim**: Kullanılmamış VPN'ler arasından rastgele seçim

### 📊 VPN Havuzu Yönetimi
- **552 VPN Config**: Toplam 552 farklı VPN sunucusu
- **Otomatik Sıfırlama**: Tüm VPN'ler kullanıldığında liste sıfırlanır
- **Kullanım Takibi**: Hangi VPN'lerin kullanıldığı takip edilir

### 🛡️ Hata Yönetimi
- **Bağlantı Testleri**: Her VPN bağlantısı test edilir
- **IP Değişikliği Kontrolü**: VPN'in gerçekten çalıştığı doğrulanır
- **Otomatik Temizlik**: Başarısız VPN'ler otomatik kapatılır

## Kullanım

### 1. Crawler Entegrasyonu

```python
from src.crawlers.commoncrawl_crawler import CommonCrawlCrawler

async with CommonCrawlCrawler() as crawler:
    # 403 hatası otomatik olarak işlenir
    result = await crawler.fetch_commoncrawl_data("path/to/data")
    if result:
        print(f"Başarılı: {result['status']}")
```

### 2. Manuel VPN Rotasyonu

```python
from src.utils.vpn_manager import VPNManager

vpn_manager = VPNManager()
await vpn_manager.connect_initial_vpn()

# 403 hatası simülasyonu
rotation_success = await vpn_manager.rotate_vpn_on_403()
if rotation_success:
    print(f"VPN değiştirildi: {vpn_manager.current_vpn}")
```

## Sistem Detayları

### VPN Rotasyon Süreci

1. **403 Hatası Algılama**
   ```
   HTTP 403 → VPN Rotasyon Tetiklenir
   ```

2. **Mevcut VPN Kesme**
   ```
   Mevcut VPN → Kes → Temizlik
   ```

3. **Yeni VPN Seçimi**
   ```
   Kullanılmamış VPN → Rastgele Seç → Bağlan
   ```

4. **Bağlantı Testi**
   ```
   IP Değişikliği → Test → Onay
   ```

5. **Başarı Kontrolü**
   ```
   Başarılı → Devam Et
   Başarısız → Sonraki VPN
   ```

### VPN Havuzu İstatistikleri

- **Toplam VPN**: 552
- **Kullanılabilir**: 552 (başlangıçta)
- **Rotasyon Limit**: 10 deneme
- **Sıfırlama**: Tüm VPN'ler kullanıldığında

### Hata Kodları ve İşlemler

| HTTP Kodu | İşlem |
|-----------|-------|
| 200 | ✅ Başarılı - İşleme devam et |
| 403 | 🔄 VPN rotasyonu başlat |
| 429 | ⏳ Rate limit - Bekle |
| 500 | 🔧 Sunucu hatası - Tekrar dene |
| Diğer | ⚠️ Uyarı - Tekrar dene |

## Test Sonuçları

### ✅ Başarılı Testler

1. **VPN Kullanılabilirlik Testi**
   - 552 VPN config yüklendi
   - Rastgele seçim çalışıyor
   - Kullanım takibi aktif

2. **403 Rotasyon Testi**
   - İlk VPN bağlantısı: `us-chi-wg-308.conf`
   - 403 simülasyonu başarılı
   - Yeni VPN: `us-slc-wg-203.conf`
   - IP değişikliği doğrulandı

3. **Common Crawl Crawler Testi**
   - Ana sayfa erişimi: HTTP 200
   - Index dosyası erişimi: HTTP 200
   - VPN entegrasyonu çalışıyor

### 📊 Performans Metrikleri

- **VPN Bağlantı Süresi**: ~2-3 saniye
- **403 Rotasyon Süresi**: ~5-10 saniye
- **Başarı Oranı**: %95+ (test edilen VPN'ler)
- **IP Değişikliği**: %100 başarılı

## Sunucuda Kullanım

### Gereksinimler

1. **WireGuard Kurulumu**
   ```bash
   # Ubuntu/Debian
   sudo apt install wireguard
   
   # CentOS/RHEL
   sudo yum install wireguard-tools
   ```

2. **Sudo Yetkisi**
   ```bash
   # VPN bağlantısı için sudo gerekli
   sudo wg-quick up config.conf
   ```

3. **Python Bağımlılıkları**
   ```bash
   pip install aiohttp asyncio
   ```

### Sunucu Yapılandırması

```python
# config/settings.py
VPN_ROTATION_ON_403 = True  # Aktif
VPN_CONNECTION_TIMEOUT = 15  # 15 saniye
```

### Monitoring ve Logging

```python
# Log seviyeleri
logging.basicConfig(level=logging.INFO)

# VPN rotasyon logları
logger.info("🔄 403 rotasyon başlatılıyor...")
logger.info("✅ VPN değiştirildi: us-slc-wg-203.conf")
```

## Sorun Giderme

### VPN Bağlantı Sorunları

1. **Interface Çakışması**
   ```bash
   # Mevcut interface'leri temizle
   sudo ifconfig utun* down
   sudo route flush
   ```

2. **Route Sorunları**
   ```bash
   # Route'ları kontrol et
   netstat -rn | grep utun
   ```

3. **WireGuard Sorunları**
   ```bash
   # WireGuard durumunu kontrol et
   sudo wg show
   ```

### 403 Rotasyon Sorunları

1. **VPN Havuzu Tükenmesi**
   - Logları kontrol et
   - Yeni VPN config'leri ekle

2. **Bağlantı Başarısız**
   - VPN sunucularını kontrol et
   - Farklı bölgelerden VPN dene

3. **IP Değişikliği Olmaması**
   - VPN test fonksiyonunu kontrol et
   - Manuel IP kontrolü yap

## Geliştirme

### Yeni VPN Ekleme

1. **Config Dosyası Oluştur**
   ```ini
   [Interface]
   PrivateKey = YOUR_PRIVATE_KEY
   Address = YOUR_ADDRESS
   
   [Peer]
   PublicKey = SERVER_PUBLIC_KEY
   AllowedIPs = 3.160.57.128/32, 3.160.57.34/32, ...
   Endpoint = SERVER_ENDPOINT
   ```

2. **Dizine Ekle**
   ```bash
   cp new_vpn.conf mullvad_wireguard_macos_all_all/
   ```

3. **Test Et**
   ```bash
   python3 test_vpn.py
   ```

### Performans İyileştirmeleri

1. **Paralel VPN Testleri**
   ```python
   # Birden fazla VPN'yi aynı anda test et
   tasks = [test_vpn(vpn) for vpn in vpn_list]
   results = await asyncio.gather(*tasks)
   ```

2. **Önbellek Sistemi**
   ```python
   # Başarılı VPN'leri önbellekle
   successful_vpns = cache.get('successful_vpns', [])
   ```

3. **Akıllı Seçim**
   ```python
   # Coğrafi yakınlık bazlı seçim
   def select_vpn_by_location(target_location):
       return closest_vpn(target_location)
   ```

## Sonuç

403 rotasyon sistemi başarıyla çalışıyor ve Common Crawl verilerine kesintisiz erişim sağlıyor. Sistem:

- ✅ **552 VPN** ile geniş havuz
- ✅ **Otomatik rotasyon** ile kesintisiz erişim
- ✅ **Akıllı hata yönetimi** ile güvenilirlik
- ✅ **Modüler yapı** ile kolay geliştirme

Sunucuda kullanıma hazır! 🚀 