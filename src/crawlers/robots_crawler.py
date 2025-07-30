import asyncio
import logging
from typing import List, Set
from pathlib import Path
import tempfile
import os
from tqdm import tqdm

from src.utils.file_downloader import FileDownloader
from src.processors.wordpress_detector import WordPressDetector
from config.settings import (
    MAX_WORKERS, CHUNK_SIZE, BATCH_SIZE, 
    ROBOTSTXT_PATHS_FILE, WORDPRESS_DOMAINS_FILE
)

logger = logging.getLogger(__name__)

class RobotsCrawler:
    """Robots.txt dosyalarını paralel işleyen crawler"""
    
    def __init__(self):
        self.detector = WordPressDetector()
        self.processed_paths: Set[str] = set()
        self.total_domains_found = 0
        
    def load_paths(self) -> List[str]:
        """Paths dosyasını yükle"""
        try:
            with open(ROBOTSTXT_PATHS_FILE, 'r', encoding='utf-8') as f:
                paths = [line.strip() for line in f if line.strip()]
            logger.info(f"Toplam {len(paths)} path yüklendi")
            return paths
        except Exception as e:
            logger.error(f"Paths dosyası yükleme hatası: {e}")
            return []
    
    def chunk_paths(self, paths: List[str], chunk_size: int = CHUNK_SIZE) -> List[List[str]]:
        """Path'leri worker'lar için chunk'lara böl"""
        return [paths[i:i + chunk_size] for i in range(0, len(paths), chunk_size)]
    
    async def process_chunk(self, chunk: List[str], worker_id: int) -> List[str]:
        """Bir chunk'ı işle ve WordPress domain'lerini bul"""
        domains_found = []
        
        async with FileDownloader() as downloader:
            # Batch'ler halinde işle
            for i in range(0, len(chunk), BATCH_SIZE):
                batch = chunk[i:i + BATCH_SIZE]
                
                logger.info(f"Worker {worker_id}: Batch {i//BATCH_SIZE + 1} işleniyor ({len(batch)} dosya)")
                
                # Dosyaları indir
                results = await downloader.download_batch(batch)
                
                # Her dosyayı işle
                for path, content in results:
                    if content:
                        # WordPress domain'lerini bul
                        domains = self.detector.process_robots_file(path, content)
                        domains_found.extend(domains)
                        
                        # İstatistikleri güncelle
                        self.total_domains_found += len(domains)
                        
                        if domains:
                            logger.info(f"Worker {worker_id}: {len(domains)} domain bulundu")
                    
                    # Her dosya işlendikten sonra content'i temizle
                    del content
                
                # Belleği temizle
                del results
                
                # Garbage collection'ı zorla
                import gc
                gc.collect()
                
        return domains_found
    
    async def run_parallel_processing(self, paths: List[str]) -> List[str]:
        """Path'leri paralel işle"""
        all_domains = []
        
        # Path'leri chunk'lara böl
        chunks = self.chunk_paths(paths)
        logger.info(f"Toplam {len(chunks)} chunk oluşturuldu")
        
        # Progress bar ile işle
        with tqdm(total=len(chunks), desc="Chunks işleniyor") as pbar:
            # Her chunk için task oluştur
            tasks = []
            for i, chunk in enumerate(chunks):
                task = asyncio.create_task(self.process_chunk(chunk, i))
                tasks.append(task)
            
            # Tüm task'ları bekle
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sonuçları topla
            for result in results:
                if isinstance(result, list):
                    all_domains.extend(result)
                    pbar.update(1)
                else:
                    logger.error(f"Task hatası: {result}")
                    pbar.update(1)
        
        return all_domains
    
    def save_results(self, domains: List[str]):
        """Sonuçları dosyaya kaydet"""
        try:
            # Tekrarlayan domain'leri temizle
            unique_domains = list(set(domains))
            
            with open(WORDPRESS_DOMAINS_FILE, 'w', encoding='utf-8') as f:
                for domain in unique_domains:
                    f.write(f"{domain}\n")
                    
            logger.info(f"Toplam {len(unique_domains)} benzersiz WordPress domain'i kaydedildi")
            
        except Exception as e:
            logger.error(f"Sonuç kaydetme hatası: {e}")
    
    async def run(self):
        """Ana işlemi çalıştır"""
        logger.info("Robots.txt crawler başlatılıyor...")
        
        # Path'leri yükle
        paths = self.load_paths()
        if not paths:
            logger.error("Path'ler yüklenemedi!")
            return
        
        # Paralel işleme başlat
        domains = await self.run_parallel_processing(paths)
        
        # Sonuçları kaydet
        self.save_results(domains)
        
        logger.info(f"İşlem tamamlandı! Toplam {len(domains)} domain bulundu") 