# VPN Yapılandırması - Common Crawl Erişimi

## Genel Bakış

Bu proje, Common Crawl verilerine erişim için VPN yapılandırması kullanır. VPN sadece Common Crawl IP'lerine yönlendirilir (split tunneling), böylece diğer internet trafiği normal şekilde çalışmaya devam eder.

## Yapılandırma Detayları

### Common Crawl IP Adresleri

Common Crawl'ın güncel IP adresleri:
- `3.160.57.128/32` - data.commoncrawl.org
- `3.160.57.34/32` - data.commoncrawl.org  
- `3.160.57.125/32` - data.commoncrawl.org
- `3.160.57.65/32` - data.commoncrawl.org
- `3.160.0.0/16` - CloudFront IP range (yedek)

### VPN Config Yapısı

Örnek VPN config dosyası (`wg001.conf`):

```ini
[Interface]
# Device: Flying Boar
PrivateKey = cA1AEddgHsVGLz8tzz9Lpx8LHlZIQEbiRVtBSYABJHQ=
Address = 10.67.251.146/32,fc00:bbbb:bbbb:bb01::4:fb91/128

[Peer]
PublicKey = qD3AH8vI8MhEVc9+0+2O8zV0Gx9FfKdy7ri3Bnpzo10=
AllowedIPs = 3.160.57.128/32, 3.160.57.34/32, 3.160.57.125/32, 3.160.57.65/32, 3.160.0.0/16, 54.221.61.107/32, 34.192.139.201/32, 52.86.149.41/32, 34.197.172.56/32, 104.26.13.205/32, 172.67.74.152/32, 104.26.12.205/32
Endpoint = 185.213.193.3:51820
```

## Kullanım

### 1. VPN Test Etme

```bash
python3 test_vpn.py
```

Bu script:
- Mevcut IP'yi kontrol eder
- VPN bağlantısını kurar
- IP değişikliğini doğrular
- Common Crawl erişimini test eder
- VPN bağlantısını kapatır

### 2. VPN Manager Kullanımı

```python
from src.utils.vpn_manager import VPNManager

# VPN Manager'ı başlat
vpn_manager = VPNManager()

# VPN bağlantısını kur
success = await vpn_manager.connect_initial_vpn()

if success:
    # Common Crawl'a erişim artık VPN üzerinden
    # Normal internet trafiği etkilenmez
    pass

# Temizlik
await vpn_manager.cleanup()
```

## Özellikler

### Split Tunneling
- Sadece Common Crawl IP'leri VPN üzerinden yönlendirilir
- Diğer internet trafiği normal şekilde çalışır
- DNS ayarları değiştirilmez

### Otomatik VPN Rotasyonu
- 403 hatası alındığında otomatik VPN değiştirme
- Farklı VPN sunucuları arasında geçiş
- Başarısız VPN'leri otomatik atlama

### Hata Yönetimi
- Route zaten mevcut hatalarını otomatik işleme
- VPN bağlantı testleri
- Interface temizleme

## Test Sonuçları

✅ **VPN Bağlantısı**: Başarılı
✅ **IP Değişikliği**: Doğrulandı  
✅ **Common Crawl Erişimi**: HTTP 200
✅ **Split Tunneling**: Çalışıyor
✅ **Otomatik Temizlik**: Aktif

## Teknik Detaylar

### WireGuard Interface Yönetimi
- Benzersiz interface adları (`wg001`, `wg002`, vb.)
- Otomatik interface temizleme
- Route yönetimi

### Güvenlik
- Config dosyaları 600 izinleri ile korunur
- Private key'ler güvenli şekilde saklanır
- Sudo yetkisi sadece gerekli durumlarda kullanılır

## Sorun Giderme

### "File exists" Hatası
Bu hata normaldir ve route'ların zaten mevcut olduğunu gösterir. VPN çalışmaya devam eder.

### VPN Bağlantı Hatası
1. Interface'leri temizle: `sudo ifconfig utun* down`
2. Route'ları temizle: `sudo route flush`
3. Test script'ini tekrar çalıştır

### Common Crawl Erişim Sorunu
1. IP adreslerini güncelle: `nslookup data.commoncrawl.org`
2. VPN config'lerini yeniden oluştur
3. Farklı VPN sunucusu dene

## Geliştirme

### Yeni IP Ekleme
`src/utils/vpn_manager.py` dosyasındaki `commoncrawl_ips` listesine yeni IP'ler eklenebilir.

### Yeni VPN Config Ekleme
`mullvad_wireguard_macos_all_all/` dizinine yeni `.conf` dosyaları eklenebilir.

### Test Geliştirme
`test_vpn.py` script'i genişletilebilir:
- Daha fazla test senaryosu
- Performans testleri
- Otomatik raporlama 