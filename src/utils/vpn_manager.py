import asyncio
import subprocess
import os
import logging
import random
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class VPNManager:
    def __init__(self, vpn_configs_dir: str = "mullvad_wireguard_macos_all_all"):
        self.vpn_configs_dir = Path(vpn_configs_dir)
        self.vpn_configs = self._load_vpn_configs()
        self.current_vpn_index = 0
        self.active_connections = {}  # worker_id -> vpn_config
        
    def _load_vpn_configs(self) -> List[str]:
        """VPN config dosyalarını yükle"""
        configs = []
        if self.vpn_configs_dir.exists():
            for config_file in self.vpn_configs_dir.glob("*.conf"):
                configs.append(str(config_file))
        logger.info(f"Toplam {len(configs)} VPN config yüklendi")
        return configs
    
    def get_next_vpn_config(self, worker_id: int) -> Optional[str]:
        """Worker için sıradaki VPN config'ini al"""
        if not self.vpn_configs:
            logger.warning("VPN config bulunamadı!")
            return None
            
        # Worker için rastgele VPN seç
        vpn_config = random.choice(self.vpn_configs)
        self.active_connections[worker_id] = vpn_config
        logger.info(f"Worker {worker_id} için VPN seçildi: {os.path.basename(vpn_config)}")
        return vpn_config
    
    def rotate_vpn_for_worker(self, worker_id: int) -> Optional[str]:
        """Worker için VPN'i değiştir (403 hatası durumunda)"""
        if worker_id in self.active_connections:
            # Mevcut VPN'i kaldır
            current_vpn = self.active_connections[worker_id]
            self.vpn_configs.remove(current_vpn)
            logger.info(f"Worker {worker_id} için VPN değiştiriliyor: {os.path.basename(current_vpn)}")
        
        # Yeni VPN seç
        return self.get_next_vpn_config(worker_id)
    
    async def connect_vpn(self, worker_id: int, vpn_config: str) -> bool:
        """VPN'e bağlan"""
        try:
            # WireGuard bağlantısını başlat (sudo password olmadan)
            cmd = ["wg-quick", "up", vpn_config]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Worker {worker_id} VPN'e bağlandı: {os.path.basename(vpn_config)}")
                return True
            else:
                logger.warning(f"Worker {worker_id} VPN bağlantı hatası (sudo gerekli): {result.stderr}")
                # VPN olmadan devam et
                return True
                
        except Exception as e:
            logger.warning(f"Worker {worker_id} VPN bağlantı hatası: {e}")
            # VPN olmadan devam et
            return True
    
    async def disconnect_vpn(self, worker_id: int) -> bool:
        """VPN bağlantısını kes"""
        try:
            if worker_id in self.active_connections:
                vpn_config = self.active_connections[worker_id]
                cmd = ["wg-quick", "down", vpn_config]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    logger.info(f"Worker {worker_id} VPN bağlantısı kesildi")
                    del self.active_connections[worker_id]
                    return True
                else:
                    logger.warning(f"Worker {worker_id} VPN kesme hatası: {result.stderr}")
                    
        except Exception as e:
            logger.warning(f"Worker {worker_id} VPN kesme hatası: {e}")
            
        return True  # Her durumda True döndür
    
    def get_available_vpn_count(self) -> int:
        """Kullanılabilir VPN sayısını döndür"""
        return len(self.vpn_configs)
    
    def cleanup(self):
        """Tüm VPN bağlantılarını temizle"""
        for worker_id in list(self.active_connections.keys()):
            asyncio.create_task(self.disconnect_vpn(worker_id)) 