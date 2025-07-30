import re
import logging
import threading
from typing import List
from config.settings import WORDPRESS_PATTERNS, WORDPRESS_DOMAINS_FILE

logger = logging.getLogger(__name__)

# Thread-safe domain set'i
class DomainManager:
    def __init__(self, output_file: str):
        self.output_file = output_file
        self.domains = set()
        self.lock = threading.Lock()
        self._load_existing_domains()
    
    def _load_existing_domains(self):
        """Mevcut domain'leri yükle"""
        try:
            if self.output_file.exists():
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    existing_domains = {line.strip() for line in f if line.strip()}
                self.domains.update(existing_domains)
                logger.info(f"Mevcut {len(existing_domains)} domain yüklendi")
        except Exception as e:
            logger.error(f"Mevcut domain yükleme hatası: {e}")
    
    def add_domains(self, new_domains: List[str]) -> int:
        """Yeni domain'leri ekle ve dosyaya yaz"""
        added_count = 0
        
        with self.lock:
            for domain in new_domains:
                if domain not in self.domains:
                    self.domains.add(domain)
                    added_count += 1
                    
                    # Anlık olarak dosyaya ekle
                    try:
                        with open(self.output_file, 'a', encoding='utf-8') as f:
                            f.write(f"{domain}\n")
                    except Exception as e:
                        logger.error(f"Domain dosyaya yazma hatası: {e}")
        
        if added_count > 0:
            logger.info(f"{added_count} yeni domain eklendi (toplam: {len(self.domains)})")
        
        return added_count

class WordPressDetector:
    def __init__(self):
        self.output_file = WORDPRESS_DOMAINS_FILE
        self.domain_manager = DomainManager(self.output_file)
    
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
                        
                        # www. ile başlıyorsa kaldır
                        if current_domain.startswith('www.'):
                            current_domain = current_domain[4:]
                        
                        # DEBUG logunu kaldırdım
                
                # Content-Type kontrolü
                elif line.startswith('Content-Type:') and 'text/plain' in line:
                    # DEBUG logunu kaldırdım
                    pass
                
                # WordPress pattern kontrolü
                elif current_domain and any(pattern in line for pattern in WORDPRESS_PATTERNS):
                    if current_domain not in domains:  # Tekrar ekleme
                        domains.append(current_domain)
                        logger.info(f"WordPress pattern bulundu: {current_domain} - {line[:50]}...")
                    # break kaldırıldı - tüm pattern'leri ara
            
            # DEBUG loglarını kaldırdım
                
        except Exception as e:
            logger.error(f"Domain çıkarma hatası: {e}")
        
        return domains
    
    def detect_wordpress_in_content(self, content: str) -> bool:
        """İçerikte WordPress belirteci var mı kontrol et"""
        for pattern in WORDPRESS_PATTERNS:
            if pattern in content:
                # DEBUG logunu kaldırdım
                return True
        return False
    
    def process_robots_file(self, path: str, content: str) -> List[str]:
        """Robots.txt dosyasını işle ve WordPress domain'lerini bul"""
        # DEBUG logunu kaldırdım
        
        if not content:
            # DEBUG logunu kaldırdım
            return []
        
        # WordPress kontrolü
        if self.detect_wordpress_in_content(content):
            domains = self.extract_domains_from_robots_content(content)
            if domains:
                # Domain'leri anlık olarak ekle
                added_count = self.domain_manager.add_domains(domains)
                if added_count > 0:
                    logger.info(f"WordPress domain bulundu ve eklendi: {domains[0]} ({path})")
            return domains
        else:
            # DEBUG logunu kaldırdım
            return []
    
    def save_domains(self, domains: List[str], output_file: str):
        """Domain'leri dosyaya kaydet (artık kullanılmıyor, anlık ekleme var)"""
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
    
    def get_total_domains(self) -> int:
        """Toplam domain sayısını döndür"""
        return len(self.domain_manager.domains)
    
    def process_chunk(self, content: str):
        """İçerik chunk'ını işle ve WordPress domain'lerini bul"""
        try:
            # WordPress kontrolü
            if self.detect_wordpress_in_content(content):
                domains = self.extract_domains_from_robots_content(content)
                if domains:
                    # Domain'leri anlık olarak ekle
                    added_count = self.domain_manager.add_domains(domains)
                    if added_count > 0:
                        logger.info(f"WordPress domain bulundu: {domains[0]}")
                        
        except Exception as e:
            logger.error(f"Chunk işleme hatası: {e}")
    
    def get_domain_count(self) -> int:
        """Bulunan domain sayısını döndür"""
        return len(self.domain_manager.domains) 