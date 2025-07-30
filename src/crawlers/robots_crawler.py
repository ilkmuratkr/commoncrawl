import asyncio
import logging
import gc
from typing import List, Set
from tqdm import tqdm

from config.settings import (
    ROBOTSTXT_PATHS_FILE, WORDPRESS_DOMAINS_FILE,
    MAX_WORKERS, CHUNK_SIZE, BATCH_SIZE,
    COMMONCRAWL_BASE_URL
)
from src.utils.file_downloader import FileDownloader
from src.processors.wordpress_detector import WordPressDetector
from src.utils.vpn_manager import VPNManager

logger = logging.getLogger(__name__)

# Global semaphore for connection control
GLOBAL_SEMAPHORE = asyncio.Semaphore(MAX_WORKERS)

# Global VPN rotasyon event'i
VPN_ROTATION_EVENT = asyncio.Event()

class RobotsCrawler:
    def __init__(self):
        self.wordpress_detector = WordPressDetector()
        self.vpn_manager = VPNManager()
        self.domains_found: Set[str] = set()
        
    def load_paths(self) -> List[str]:
        """Paths dosyasını yükle"""
        try:
            with open(ROBOTSTXT_PATHS_FILE, 'r') as f:
                paths = [line.strip() for line in f if line.strip()]
            logger.info(f"{len(paths)} path yüklendi")
            return paths
        except FileNotFoundError:
            logger.error(f"Paths dosyası bulunamadı: {ROBOTSTXT_PATHS_FILE}")
            return []
    
    def chunk_paths(self, paths: List[str]) -> List[List[str]]:
        """Paths'leri chunk'lara böl"""
        chunks = []
        for i in range(0, len(paths), CHUNK_SIZE):
            chunk = paths[i:i + CHUNK_SIZE]
            chunks.append(chunk)
        logger.info(f"{len(chunks)} chunk oluşturuldu")
        return chunks
    
    async def handle_403_error(self, worker_id: int):
        """403 hatası durumunda global VPN rotasyonu"""
        logger.warning(f"Worker {worker_id}: 403 hatası tespit edildi, global VPN rotasyonu başlatılıyor...")
        
        # Tüm worker'ları durdur
        VPN_ROTATION_EVENT.set()
        
        # VPN değiştir
        success = await self.vpn_manager.rotate_vpn_on_403()
        if success:
            logger.info(f"Worker {worker_id}: VPN değiştirildi, işlem devam ediyor...")
            # Kısa bekleme
            await asyncio.sleep(5.0)
        else:
            logger.error(f"Worker {worker_id}: VPN değiştirme başarısız")
        
        # Event'i temizle
        VPN_ROTATION_EVENT.clear()
    
    async def process_chunk(self, chunk: List[str], worker_id: int) -> List[str]:
        """Tek chunk'ı işle"""
        domains_found = []
        total_files_processed = 0
        wordpress_files_found = 0
        
        try:
            # Chunk başında VPN bağlantısını kontrol et
            if worker_id == 0:  # İlk worker VPN'i başlatsın
                logger.info("Split tunneling VPN bağlantısı kuruluyor ve test ediliyor...")
                vpn_success = await self.vpn_manager.connect_initial_vpn()
                if not vpn_success:
                    logger.error("Split tunneling VPN bağlantısı başarısız! İşlem durduruluyor.")
                    return domains_found
                logger.info("Split tunneling VPN bağlantısı başarılı, işlem başlıyor...")
            
            logger.info(f"Worker {worker_id}: {len(chunk)} dosya işlenecek")
            
            async with GLOBAL_SEMAPHORE:
                # Chunk'ı batch'lere böl
                for i in range(0, len(chunk), BATCH_SIZE):
                    batch = chunk[i:i + BATCH_SIZE]
                    batch_num = i // BATCH_SIZE + 1
                    total_batches = (len(chunk) + BATCH_SIZE - 1) // BATCH_SIZE
                    
                    logger.info(f"Worker {worker_id}: Batch {batch_num}/{total_batches} işleniyor ({len(batch)} dosya)")
                    
                    try:
                        # Batch'i indir
                        async with FileDownloader() as downloader:
                            results = await downloader.download_batch(batch)
                        
                        # Her dosyayı işle
                        batch_domains = 0
                        batch_files_processed = 0
                        
                        for path, content in results:
                            if content:
                                try:
                                    batch_files_processed += 1
                                    total_files_processed += 1
                                    
                                    # WordPress kontrolü
                                    domains = self.wordpress_detector.process_robots_file(path, content)
                                    if domains:
                                        domains_found.extend(domains)
                                        batch_domains += len(domains)
                                        wordpress_files_found += 1
                                        logger.info(f"Worker {worker_id}: WordPress bulundu - {domains[0]}")
                                    
                                    # Memory temizliği
                                    del content
                                    gc.collect()
                                    
                                except Exception as e:
                                    logger.error(f"Dosya işleme hatası {path}: {e}")
                        
                        if batch_domains > 0:
                            logger.info(f"Worker {worker_id}: Batch {batch_num} tamamlandı - {batch_domains} WordPress domain bulundu")
                        else:
                            logger.info(f"Worker {worker_id}: Batch {batch_num} tamamlandı - WordPress bulunamadı")
                        
                        # Batch'ler arası kısa bekleme
                        await asyncio.sleep(2.0)
                        
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "403" in error_msg or "forbidden" in error_msg:
                            # Global VPN rotasyonu
                            await self.handle_403_error(worker_id)
                        else:
                            logger.error(f"Batch işleme hatası: {e}")
                
                logger.info(f"Worker {worker_id}: Chunk tamamlandı - {len(domains_found)} WordPress domain bulundu ({wordpress_files_found}/{total_files_processed} dosyada)")
                
        except Exception as e:
            logger.error(f"Chunk işleme hatası (Worker {worker_id}): {e}")
        
        return domains_found
    
    async def run_parallel_processing(self, chunks: List[List[str]]):
        """Paralel işleme çalıştır"""
        tasks = []
        
        for i, chunk in enumerate(chunks):
            task = asyncio.create_task(self.process_chunk(chunk, i))
            tasks.append(task)
        
        # Progress bar ile işle
        with tqdm(total=len(chunks), desc="Chunks işleniyor") as pbar:
            for task in asyncio.as_completed(tasks):
                try:
                    domains = await task
                    self.domains_found.update(domains)
                    pbar.update(1)
                except Exception as e:
                    logger.error(f"Task hatası: {e}")
                    pbar.update(1)
    
    def save_results(self):
        """Sonuçları kaydet (artık anlık ekleme var)"""
        total_domains = self.wordpress_detector.get_total_domains()
        logger.info(f"Toplam {total_domains} benzersiz WordPress domain bulundu ve kaydedildi")
        
        # İlk 5 domain'i göster
        try:
            with open(WORDPRESS_DOMAINS_FILE, 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
            
            if domains:
                logger.info("İlk 5 domain:")
                for i, domain in enumerate(domains[:5]):
                    logger.info(f"  {i+1}. {domain}")
        except Exception as e:
            logger.error(f"Domain listesi okuma hatası: {e}")
    
    async def run(self):
        """Ana crawler işlemini çalıştır"""
        try:
            logger.info("WordPress Domain Crawler başlatılıyor...")
            
            # Paths'i yükle
            paths = self.load_paths()
            if not paths:
                logger.error("Paths yüklenemedi, çıkılıyor")
                return
            
            # Chunk'lara böl
            chunks = self.chunk_paths(paths)
            
            # Paralel işleme
            await self.run_parallel_processing(chunks)
            
            # Sonuçları kaydet
            self.save_results()
            
            logger.info("Crawler tamamlandı!")
            
        except KeyboardInterrupt:
            logger.info("Kullanıcı tarafından durduruldu")
        except Exception as e:
            logger.error(f"Crawler hatası: {e}")
        finally:
            # VPN temizliği
            await self.vpn_manager.cleanup() 