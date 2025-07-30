#!/usr/bin/env python3
"""
403 Rotasyon Test Script'i
VPN rotasyon sistemini test eder
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

async def simulate_403_rotation():
    """403 rotasyon sistemini simüle et"""
    print("🔄 403 Rotasyon Testi Başlıyor...")
    print("=" * 50)
    
    # VPN Manager'ı başlat
    vpn_manager = VPNManager()
    print(f"📁 {len(vpn_manager.vpn_configs)} VPN config yüklendi")
    print()
    
    # İlk VPN bağlantısını kur
    print("1️⃣ İlk VPN bağlantısı kuruluyor...")
    success = await vpn_manager.connect_initial_vpn()
    
    if not success:
        print("❌ İlk VPN bağlantısı başarısız!")
        return
    
    print("✅ İlk VPN bağlantısı başarılı!")
    print(f"🔗 Aktif VPN: {vpn_manager.current_vpn}")
    print()
    
    # 403 rotasyon simülasyonu
    print("2️⃣ 403 rotasyon simülasyonu...")
    print("🔄 VPN değiştiriliyor (403 hatası simülasyonu)...")
    
    rotation_success = await vpn_manager.rotate_vpn_on_403()
    
    if rotation_success:
        print("✅ 403 rotasyon başarılı!")
        print(f"🔗 Yeni VPN: {vpn_manager.current_vpn}")
    else:
        print("❌ 403 rotasyon başarısız!")
    
    print()
    
    # Temizlik
    print("3️⃣ Temizlik yapılıyor...")
    await vpn_manager.cleanup()
    print("✅ VPN bağlantısı kapatıldı")
    
    print()
    print("=" * 50)
    print("🏁 403 Rotasyon Testi Tamamlandı!")

async def test_vpn_availability():
    """VPN kullanılabilirliğini test et"""
    print("🔍 VPN Kullanılabilirlik Testi...")
    print("=" * 50)
    
    vpn_manager = VPNManager()
    
    print(f"📊 Toplam VPN sayısı: {len(vpn_manager.vpn_configs)}")
    print(f"🔄 Kullanılan VPN sayısı: {len(vpn_manager.used_vpns)}")
    print(f"✅ Kullanılabilir VPN sayısı: {len(vpn_manager.vpn_configs) - len(vpn_manager.used_vpns)}")
    
    # İlk 10 VPN'yi test et
    print("\n🔍 İlk 10 VPN test ediliyor...")
    for i in range(10):
        vpn = vpn_manager.get_available_vpn()
        if vpn:
            print(f"   {i+1:2d}. {vpn}")
        else:
            print(f"   {i+1:2d}. VPN bulunamadı!")
    
    print()
    print("=" * 50)

async def main():
    """Ana fonksiyon"""
    print("🚀 VPN 403 Rotasyon Test Sistemi")
    print("=" * 50)
    
    # VPN kullanılabilirlik testi
    await test_vpn_availability()
    
    print()
    
    # 403 rotasyon simülasyonu
    await simulate_403_rotation()

if __name__ == "__main__":
    asyncio.run(main()) 