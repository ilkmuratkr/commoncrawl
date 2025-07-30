import os
from pathlib import Path

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent

# Veri dizinleri
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"

# Dosya yolları
ROBOTSTXT_PATHS_FILE = PROJECT_ROOT / "robotstxt.paths (1)"  # Tam ölçekli çalışma
WORDPRESS_DOMAINS_FILE = RESULTS_DIR / "wordpress_domains.txt"

# Crawler ayarları
MAX_WORKERS = 1  # Tek worker kullanacağız
CHUNK_SIZE = 50  # Daha küçük chunk'lar
BATCH_SIZE = 5   # Daha küçük batch'ler

# HTTP ayarları
REQUEST_TIMEOUT = 60  # Normal timeout
MAX_RETRIES = 3      # Normal retry
RETRY_DELAY = 2      # Normal retry delay

# CommonCrawl base URL
COMMONCRAWL_BASE_URL = "https://data.commoncrawl.org/"

# WordPress belirteçleri
WORDPRESS_PATTERNS = [
    "wp-",
    "wp-content",
    "wp-includes", 
    "wp-admin",
    "wordpress"
]

# VPN ayarları
VPN_CONFIG_DIR = "mullvad_wireguard_macos_all_all"
VPN_ROTATION_ON_403 = True  # 403 hatası alınca VPN değiştir
VPN_CONNECTION_TIMEOUT = 15  # VPN bağlantı timeout'u (30'dan 15'e düşürdüm)

# Dizinleri oluştur
for directory in [DATA_DIR, RAW_DIR, PROCESSED_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True) 