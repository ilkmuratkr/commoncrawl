#!/usr/bin/env python3
"""
VPN Config Güncelleme Script'i
Tüm VPN config dosyalarını Common Crawl IP'leri ile günceller
"""

import os
import glob
from pathlib import Path

# Common Crawl IP'leri
COMMONCRAWL_IPS = [
    "3.160.57.128/32",   # data.commoncrawl.org IP
    "3.160.57.34/32",    # data.commoncrawl.org IP
    "3.160.57.125/32",   # data.commoncrawl.org IP
    "3.160.57.65/32",    # data.commoncrawl.org IP
    "3.160.0.0/16",      # CloudFront IP range
    # Test siteleri IP'leri
    "54.221.61.107/32",  # httpbin.org IP
    "34.192.139.201/32", # httpbin.org IP
    "52.86.149.41/32",   # httpbin.org IP
    "34.197.172.56/32",  # httpbin.org IP
    "104.26.13.205/32",  # api.ipify.org IP
    "172.67.74.152/32",  # api.ipify.org IP
    "104.26.12.205/32",  # api.ipify.org IP
]

def update_vpn_config(config_path):
    """VPN config dosyasını güncelle"""
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        new_lines = []
        updated = False
        
        for line in lines:
            if line.startswith('AllowedIPs = '):
                # AllowedIPs satırını güncelle
                new_line = f"AllowedIPs = {', '.join(COMMONCRAWL_IPS)}"
                new_lines.append(new_line)
                updated = True
            elif line.startswith('DNS = '):
                # DNS satırını kaldır
                continue
            else:
                new_lines.append(line)
        
        if updated:
            with open(config_path, 'w') as f:
                f.write('\n'.join(new_lines))
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Hata: {config_path} - {e}")
        return False

def main():
    """Ana fonksiyon"""
    vpn_dir = "mullvad_wireguard_macos_all_all"
    
    if not os.path.exists(vpn_dir):
        print(f"VPN dizini bulunamadı: {vpn_dir}")
        return
    
    # Tüm .conf dosyalarını bul
    config_files = glob.glob(os.path.join(vpn_dir, "*.conf"))
    
    print(f"🔧 VPN Config Güncelleme Başlıyor...")
    print(f"📁 Toplam {len(config_files)} config dosyası bulundu")
    print()
    
    updated_count = 0
    skipped_count = 0
    
    for config_file in config_files:
        filename = os.path.basename(config_file)
        
        if update_vpn_config(config_file):
            print(f"✅ Güncellendi: {filename}")
            updated_count += 1
        else:
            print(f"⏭️  Atlanıyor: {filename}")
            skipped_count += 1
    
    print()
    print("=" * 50)
    print(f"🏁 Güncelleme Tamamlandı!")
    print(f"✅ Güncellenen: {updated_count}")
    print(f"⏭️  Atlanan: {skipped_count}")
    print(f"📊 Toplam: {len(config_files)}")
    print()
    print("🔗 Common Crawl IP'leri:")
    for ip in COMMONCRAWL_IPS:
        print(f"   • {ip}")

if __name__ == "__main__":
    main() 