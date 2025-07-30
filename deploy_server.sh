#!/bin/bash

# 🚀 Common Crawl VPN Deployment Script
# Sunucuda otomatik kurulum ve çalıştırma

set -e  # Hata durumunda dur

echo "🔧 Common Crawl VPN Deployment Başlıyor..."
echo "=========================================="

# 1. Sistem güncellemesi
echo "📦 Sistem güncelleniyor..."
sudo apt update -y
sudo apt upgrade -y

# 2. Gereksinimler kurulumu
echo "📥 Gereksinimler kuruluyor..."
sudo apt install -y wireguard wireguard-tools python3 python3-pip git curl wget

# 3. Python bağımlılıkları
echo "🐍 Python bağımlılıkları kuruluyor..."
pip3 install aiohttp asyncio requests

# 4. Proje dizini oluştur
echo "📁 Proje dizini hazırlanıyor..."
cd /opt
sudo git clone https://github.com/ilkmuratkr/commoncrawl.git
sudo chown -R $USER:$USER commoncrawl
cd commoncrawl

# 5. VPN config izinleri
echo "🔐 VPN config izinleri ayarlanıyor..."
chmod 600 mullvad_wireguard_macos_all_all/*.conf

# 6. Test et
echo "🧪 Sistem test ediliyor..."
python3 test_vpn.py

echo "✅ Kurulum tamamlandı!"
echo ""
echo "🎯 Kullanım:"
echo "cd /opt/commoncrawl"
echo "python3 src/crawlers/commoncrawl_crawler.py"
echo ""
echo "📊 VPN Durumu:"
echo "python3 test_vpn.py"
echo ""
echo "🔄 403 Rotasyon Testi:"
echo "python3 test_403_rotation.py" 