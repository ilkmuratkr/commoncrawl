#!/usr/bin/env python3
"""
VPN Bağlantı Test Scripti
"""

import asyncio
import aiohttp
import logging
from src.utils.vpn_manager import VPNManager

# Logging ayarla
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_current_ip():
    """Mevcut IP'yi al - birden fazla servis dene"""
    ip_services = [
        'https://httpbin.org/ip',
        'https://api.ipify.org?format=json',
        'https://ipinfo.io/json',
        'https://api.myip.com'
    ]
    
    for service in ip_services:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(service) as response:
                    if response.status == 200:
                        data = await response.json()
                        if service == 'https://httpbin.org/ip':
                            return data.get('origin', '')
                        elif service == 'https://api.ipify.org?format=json':
                            return data.get('ip', '')
                        elif service == 'https://ipinfo.io/json':
                            return data.get('ip', '')
                        elif service == 'https://api.myip.com':
                            return data.get('ip', '')
        except Exception as e:
            print(f"   ⚠️ {service} başarısız: {e}")
            continue
    
    return None

async def test_vpn_connection():
    """VPN bağlantısını test et"""
    vpn_manager = VPNManager()
    
    print("🔍 VPN Bağlantı Testi Başlıyor...")
    print("=" * 50)
    
    # 1. Mevcut IP'yi kontrol et
    print("1️⃣ Mevcut IP kontrol ediliyor...")
    current_ip = await get_current_ip()
    if current_ip:
        print(f"   📍 Mevcut IP: {current_ip}")
    else:
        print("   ❌ IP kontrolü başarısız")
        return
    
    # 2. VPN config'leri yükleniyor...
    print("\n2️⃣ VPN config'leri yükleniyor...")
    vpn_configs = vpn_manager._load_vpn_configs()
    if vpn_configs:
        print(f"   📁 {len(vpn_configs)} VPN config bulundu")
    else:
        print("   ❌ VPN config bulunamadı")
        return
    
    # 2.5. Mevcut interface'leri temizle
    print("\n2️⃣.5️⃣ Mevcut WireGuard interface'leri temizleniyor...")
    await vpn_manager.cleanup_existing_interfaces()
    
    # 3. İlk VPN'i seç ve bağlan
    print("\n3️⃣ İlk VPN'e bağlanılıyor...")
    vpn_config = vpn_manager.get_available_vpn()
    print(f"   🔗 Seçilen VPN: {vpn_config}")
    
    # 4. VPN'e bağlan (5 farklı VPN dene)
    print("\n4️⃣ VPN bağlantısı kuruluyor (5 farklı VPN deneniyor)...")
    
    max_vpn_attempts = 5
    for attempt in range(max_vpn_attempts):
        print(f"\n   🔄 VPN Deneme {attempt + 1}/{max_vpn_attempts}")
        
        # Yeni VPN seç
        vpn_config = vpn_manager.get_available_vpn()
        if not vpn_config:
            print("   ❌ Kullanılabilir VPN config bulunamadı")
            break
            
        print(f"   🔗 Seçilen VPN: {vpn_config}")
        
        # VPN'e bağlan
        success = await vpn_manager._connect_vpn(vpn_config)
        
        if success:
            print("   ✅ VPN bağlantısı başarılı!")
            
            # 5. Yeni IP'yi kontrol et
            print("\n5️⃣ Yeni IP kontrol ediliyor...")
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get('https://api.ipify.org?format=json') as response:
                        if response.status == 200:
                            data = await response.json()
                            new_ip = data.get('ip', '')
                            print(f"   📍 Yeni IP: {new_ip}")
                            
                            if new_ip != current_ip:
                                print("   ✅ IP değişti! VPN çalışıyor!")
                                
                                # 6. CommonCrawl'a test isteği gönder
                                print("\n6️⃣ CommonCrawl'a test isteği gönderiliyor...")
                                try:
                                    test_url = "https://data.commoncrawl.org/crawl-data/CC-MAIN-2025-30/segments/1751905933612.63/robotstxt/CC-MAIN-20250707183638-20250707213638-00000.warc.gz"
                                    timeout = aiohttp.ClientTimeout(total=10)
                                    async with aiohttp.ClientSession(timeout=timeout) as session:
                                        async with session.head(test_url) as response:
                                            print(f"   📡 HTTP Status: {response.status}")
                                            if response.status == 200:
                                                print("   ✅ CommonCrawl erişimi başarılı!")
                                                print("   🎉 VPN testi başarılı! Bu VPN kullanılabilir.")
                                                
                                                # 7. VPN'i kapat
                                                print("\n7️⃣ VPN bağlantısı kapatılıyor...")
                                                await vpn_manager._disconnect_vpn(vpn_config)
                                                print("   ✅ VPN bağlantısı kapatıldı")
                                                return
                                            elif response.status == 403:
                                                print("   ❌ CommonCrawl erişimi engellendi (403)")
                                            else:
                                                print(f"   ⚠️ Beklenmeyen durum: {response.status}")
                                except Exception as e:
                                    print(f"   ❌ CommonCrawl test hatası: {e}")
                            else:
                                print("   ❌ IP değişmedi! VPN çalışmıyor!")
                        else:
                            print(f"   ❌ Yeni IP kontrolü başarısız: HTTP {response.status}")
            except Exception as e:
                print(f"   ❌ Yeni IP kontrolü hatası: {e}")
            
            # VPN'i kapat ve devam et
            await vpn_manager._disconnect_vpn(vpn_config)
            print("   🔄 VPN kapatıldı, sıradaki deneniyor...")
            
        else:
            print("   ❌ VPN bağlantısı başarısız!")
        
        # Kısa bekleme
        await asyncio.sleep(1)
    
    print("   ❌ 5 VPN denemesi sonrası başarılı bağlantı bulunamadı!")
    
    print("\n" + "=" * 50)
    print("🏁 VPN Test Tamamlandı!")

if __name__ == "__main__":
    asyncio.run(test_vpn_connection()) 