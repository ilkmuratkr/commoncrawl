#!/usr/bin/env python3
"""
VPN Bağlantı Test Script'i
Common Crawl erişimi için VPN yapılandırmasını test eder
"""

import asyncio
import logging
import aiohttp
from src.utils.vpn_manager import VPNManager

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def get_current_ip():
    """Mevcut IP adresini al"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get('https://api.ipify.org?format=json') as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('ip', 'Bilinmiyor')
    except Exception as e:
        return f"Hata: {e}"

async def test_commoncrawl_access():
    """Common Crawl erişimini test et"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get('https://data.commoncrawl.org/') as response:
                if response.status == 200:
                    return True, f"✅ Common Crawl erişimi başarılı (Status: {response.status})"
                else:
                    return False, f"❌ Common Crawl erişimi başarısız (Status: {response.status})"
    except Exception as e:
        return False, f"❌ Common Crawl erişim hatası: {e}"

async def main():
    print("🔍 VPN Bağlantı Testi Başlıyor...")
    print("=" * 50)
    
    # 1. Mevcut IP kontrol et
    print("1️⃣ Mevcut IP kontrol ediliyor...")
    original_ip = await get_current_ip()
    print(f"   📍 Mevcut IP: {original_ip}")
    print()
    
    # 2. VPN Manager'ı başlat
    print("2️⃣ VPN Manager başlatılıyor...")
    vpn_manager = VPNManager()
    print(f"   📁 {len(vpn_manager.vpn_configs)} VPN config bulundu")
    print()
    
    # 3. Mevcut interface'leri temizle
    print("2️⃣.5️⃣ Mevcut WireGuard interface'leri temizleniyor...")
    await vpn_manager.cleanup_existing_interfaces()
    print()
    
    # 4. VPN bağlantısını kur
    print("3️⃣ VPN bağlantısı kuruluyor...")
    success = await vpn_manager.connect_initial_vpn()
    
    if success:
        print("   ✅ VPN bağlantısı başarılı!")
        
        # 5. Yeni IP'yi kontrol et
        print("4️⃣ VPN sonrası IP kontrol ediliyor...")
        new_ip = await get_current_ip()
        print(f"   📍 Yeni IP: {new_ip}")
        
        if new_ip != original_ip:
            print("   ✅ IP değişikliği başarılı!")
        else:
            print("   ⚠️  IP değişikliği olmadı")
        
        # 6. Common Crawl erişimini test et
        print("5️⃣ Common Crawl erişimi test ediliyor...")
        access_success, access_message = await test_commoncrawl_access()
        print(f"   {access_message}")
        
        if access_success:
            print("   🎉 VPN yapılandırması tamamen başarılı!")
        else:
            print("   ⚠️  Common Crawl erişiminde sorun var")
        
    else:
        print("   ❌ VPN bağlantısı başarısız!")
    
    # 7. Temizlik
    print("6️⃣ Temizlik yapılıyor...")
    await vpn_manager.cleanup()
    print("   ✅ VPN bağlantısı kapatıldı")
    
    print()
    print("=" * 50)
    print("🏁 VPN Test Tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main()) 