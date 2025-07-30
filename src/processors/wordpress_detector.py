import re
import logging
from typing import List, Set, Optional
from urllib.parse import urlparse

from config.settings import WORDPRESS_PATTERNS

logger = logging.getLogger(__name__)

class WordPressDetector:
    """Robots.txt dosyalarında WordPress belirteçlerini tespit eden sınıf"""
    
    def __init__(self):
        self.wordpress_patterns = WORDPRESS_PATTERNS
        self.detected_domains: Set[str] = set()
        
    def extract_domain_from_path(self, path: str) -> Optional[str]:
        """WARC dosya yolundan domain çıkar"""
        try:
            # WARC dosya adından domain çıkarma
            # Örnek: crawl-data/CC-MAIN-2025-30/segments/1751905933612.63/robotstxt/CC-MAIN-20250707183638-20250707213638-00000.warc.gz
            # Bu durumda robots.txt içeriğinden domain çıkarmamız gerekiyor
            return None
        except Exception as e:
            logger.error(f"Domain çıkarma hatası {path}: {e}")
            return None
    
    def extract_domains_from_robots_content(self, content: str) -> List[str]:
        """Robots.txt içeriğinden domain'leri çıkar"""
        domains = set()
        
        if not content:
            return []
            
        # WARC formatını parse et
        lines = content.split('\n')
        current_domain = None
        in_robots_content = False
        
        for line in lines:
            line = line.strip()
            
            # WARC header'larını işle
            if line.startswith('WARC-Target-URI:'):
                # URL'den domain çıkar
                try:
                    url = line.split(':', 1)[1].strip()
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    current_domain = parsed.netloc
                except:
                    pass
                continue
                
            # Content-Type header'ını kontrol et
            if line.startswith('Content-Type:'):
                if 'text/plain' in line.lower():
                    in_robots_content = True
                else:
                    in_robots_content = False
                continue
                
            # WARC header'larını atla
            if line.startswith('WARC/') or line.startswith('Content-Length:') or line.startswith('WARC-'):
                continue
                
            # Robots.txt içeriğinde WordPress belirteçlerini ara
            if in_robots_content and current_domain:
                if any(pattern in line.lower() for pattern in self.wordpress_patterns):
                    domains.add(current_domain)
                    logger.debug(f"WordPress bulundu: {current_domain} - {line}")
                
        return list(domains)
    
    def detect_wordpress_in_content(self, content: str) -> bool:
        """İçerikte WordPress belirteçlerini ara"""
        if not content:
            return False
            
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in self.wordpress_patterns)
    
    def process_robots_file(self, path: str, content: str) -> List[str]:
        """Robots.txt dosyasını işle ve WordPress domain'lerini bul"""
        if not content:
            return []
            
        domains = self.extract_domains_from_robots_content(content)
        
        if domains:
            logger.info(f"WordPress domain'leri bulundu {path}: {domains}")
            
        return domains
    
    def save_domains(self, domains: List[str], output_file: str):
        """Domain'leri dosyaya kaydet"""
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                for domain in domains:
                    f.write(f"{domain}\n")
        except Exception as e:
            logger.error(f"Domain kaydetme hatası: {e}") 