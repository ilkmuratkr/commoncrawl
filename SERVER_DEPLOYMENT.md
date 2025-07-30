# 🚀 Sunucuda Deployment Kılavuzu

## Hızlı Kurulum

### 1. Deployment Script'i Çalıştır

```bash
# Script'i indir ve çalıştır
wget https://raw.githubusercontent.com/ilkmuratkr/commoncrawl/main/deploy_server.sh
chmod +x deploy_server.sh
./deploy_server.sh
```

### 2. Manuel Kurulum (Alternatif)

```bash
# Sistem güncellemesi
sudo apt update -y
sudo apt upgrade -y

# Gereksinimler
sudo apt install -y wireguard wireguard-tools python3 python3-pip git

# Python bağımlılıkları
pip3 install aiohttp asyncio requests

# Proje indir
cd /opt
sudo git clone https://github.com/ilkmuratkr/commoncrawl.git
sudo chown -R $USER:$USER commoncrawl
cd commoncrawl

# VPN config izinleri
chmod 600 mullvad_wireguard_macos_all_all/*.conf
```

## 🎯 Kullanım

### VPN Test Et
```bash
cd /opt/commoncrawl
python3 test_vpn.py
```

### Common Crawl Crawler Çalıştır
```bash
cd /opt/commoncrawl
python3 src/crawlers/commoncrawl_crawler.py
```

### 403 Rotasyon Test Et
```bash
cd /opt/commoncrawl
python3 test_403_rotation.py
```

## 🔧 Sistem Gereksinimleri

### Minimum Gereksinimler
- **OS**: Ubuntu 18.04+ / Debian 9+
- **RAM**: 2GB
- **Disk**: 10GB boş alan
- **CPU**: 2 çekirdek

### Önerilen Gereksinimler
- **OS**: Ubuntu 20.04+ / Debian 11+
- **RAM**: 4GB+
- **Disk**: 20GB+ boş alan
- **CPU**: 4+ çekirdek

## 🛠️ Sorun Giderme

### VPN Bağlantı Sorunu
```bash
# WireGuard durumu kontrol et
sudo wg show

# VPN config test et
sudo wg-quick up mullvad_wireguard_macos_all_all/wg001.conf
sudo wg-quick down mullvad_wireguard_macos_all_all/wg001.conf
```

### Python Import Hatası
```bash
# Python path kontrol et
python3 -c "import sys; print(sys.path)"

# Bağımlılıkları yeniden kur
pip3 install --upgrade aiohttp asyncio requests
```

### İzin Sorunları
```bash
# VPN config izinlerini düzelt
chmod 600 mullvad_wireguard_macos_all_all/*.conf

# Proje dizini izinlerini düzelt
sudo chown -R $USER:$USER /opt/commoncrawl
```

## 📊 Monitoring

### VPN Durumu Kontrol Et
```bash
# Aktif VPN bağlantıları
sudo wg show

# IP adresi kontrol et
curl -s https://api.ipify.org
```

### Log Kontrol Et
```bash
# Sistem logları
sudo journalctl -u wg-quick@wg001

# Python logları
tail -f /opt/commoncrawl/crawler.log
```

## 🔄 Otomatik Çalıştırma

### Systemd Service Oluştur
```bash
sudo tee /etc/systemd/system/commoncrawl-crawler.service << EOF
[Unit]
Description=Common Crawl VPN Crawler
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/commoncrawl
ExecStart=/usr/bin/python3 src/crawlers/commoncrawl_crawler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service'i etkinleştir
sudo systemctl enable commoncrawl-crawler
sudo systemctl start commoncrawl-crawler
```

### Cron Job Oluştur
```bash
# Cron job ekle
crontab -e

# Her saat başı çalıştır
0 * * * * cd /opt/commoncrawl && python3 src/crawlers/commoncrawl_crawler.py
```

## 🚨 Güvenlik Notları

1. **VPN Config Güvenliği**: VPN config dosyaları sadece root kullanıcısı tarafından okunabilir olmalı
2. **Firewall**: Gerekli portları aç (51820 UDP)
3. **Log Rotasyonu**: Log dosyalarını düzenli olarak temizle
4. **Backup**: VPN config'leri yedekle

## 📈 Performans Optimizasyonu

### Sistem Ayarları
```bash
# Network buffer'ları artır
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# File descriptor limit'ini artır
echo '* soft nofile 65536' | sudo tee -a /etc/security/limits.conf
echo '* hard nofile 65536' | sudo tee -a /etc/security/limits.conf
```

### Python Optimizasyonu
```bash
# Python performans ayarları
export PYTHONOPTIMIZE=1
export PYTHONUNBUFFERED=1
```

## 🎯 Sonuç

Bu deployment ile:
- ✅ 552 VPN sunucusu hazır
- ✅ Otomatik 403 rotasyonu
- ✅ Split tunneling aktif
- ✅ Common Crawl erişimi
- ✅ Monitoring ve logging
- ✅ Otomatik çalıştırma seçenekleri

Sunucuda `./deploy_server.sh` çalıştırarak sistemi kurabilirsin! 