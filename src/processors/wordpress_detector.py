import re
import logging
from typing import List
from config.settings import WORDPRESS_PATTERNS, WORDPRESS_DOMAINS_FILE

logger = logging.getLogger(__name__)

class WordPressDetector:
    def __init__(self):
        self.output_file = WORDPRESS_DOMAINS_FILE
    
    def extract_domains_from_robots_content(self, content: str) -> List[str]:
        """Robots.txt içeriğinden domain'leri çıkar"""
        domains = []
        
        try:
            lines = content.split('\n')
            current_domain = None
            
            for line in lines:
                line = line.strip()
                
                # WARC header'larını kontrol et
                if line.startswith('WARC-Target-URI:'):
                    # URL'den domain çıkar
                    uri = line.split(':', 1)[1].strip()
                    if uri.startswith('http'):
                        from urllib.parse import urlparse
                        parsed = urlparse(uri)
                        current_domain = parsed.netloc
                        logger.debug(f"Domain bulundu: {current_domain}")
                
                # Content-Type kontrolü
                elif line.startswith('Content-Type:') and 'text/plain' in line:
                    logger.debug("Content-Type text/plain doğrulandı")
                
                # WordPress pattern kontrolü
                elif current_domain and any(pattern in line for pattern in WORDPRESS_PATTERNS):
                    domains.append(current_domain)
                    logger.info(f"WordPress pattern bulundu: {current_domain} - {line[:50]}...")
                    break  # Bir pattern bulunduysa yeterli
            
            if domains:
                logger.debug(f"Toplam {len(domains)} domain bulundu")
            else:
                logger.debug("WordPress pattern bulunamadı")
                
        except Exception as e:
            logger.error(f"Domain çıkarma hatası: {e}")
        
        return domains
    
    def detect_wordpress_in_content(self, content: str) -> bool:
        """İçerikte WordPress belirteci var mı kontrol et"""
        for pattern in WORDPRESS_PATTERNS:
            if pattern in content:
                logger.debug(f"WordPress pattern bulundu: {pattern}")
                return True
        return False
    
    def process_robots_file(self, path: str, content: str) -> List[str]:
        """Robots.txt dosyasını işle ve WordPress domain'lerini bul"""
        logger.debug(f"İşleniyor: {path}")
        
        if not content:
            logger.debug(f"Boş içerik: {path}")
            return []
        
        # WordPress kontrolü
        if self.detect_wordpress_in_content(content):
            domains = self.extract_domains_from_robots_content(content)
            if domains:
                logger.info(f"WordPress domain bulundu: {domains[0]} ({path})")
            return domains
        else:
            logger.debug(f"WordPress pattern bulunamadı: {path}")
            return []
    
    def save_domains(self, domains: List[str], output_file: str):
        """Domain'leri dosyaya kaydet"""
        try:
            # Tekrarlayan domain'leri temizle
            unique_domains = list(set(domains))
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for domain in unique_domains:
                    f.write(f"{domain}\n")
            
            logger.info(f"Toplam {len(unique_domains)} benzersiz domain kaydedildi: {output_file}")
            
            # İlk 5 domain'i göster
            if unique_domains:
                logger.info("İlk 5 domain:")
                for i, domain in enumerate(unique_domains[:5]):
                    logger.info(f"  {i+1}. {domain}")
                    
        except Exception as e:
            logger.error(f"Domain kaydetme hatası: {e}") 