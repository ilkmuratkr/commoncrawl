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

# Worker ayarları
MAX_WORKERS = 5  # Optimize edilmiş worker sayısı
CHUNK_SIZE = 200  # Her worker'ın işleyeceği path sayısı
BATCH_SIZE = 20  # Her seferde indirilecek dosya sayısı

# HTTP ayarları
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1

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

# Dizinleri oluştur
for directory in [DATA_DIR, RAW_DIR, PROCESSED_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True) 