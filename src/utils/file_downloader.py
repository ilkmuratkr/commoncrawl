import aiohttp
import asyncio
import gzip
import logging
from typing import List, Tuple, Optional
from config.settings import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, COMMONCRAWL_BASE_URL, MAX_WORKERS

logger = logging.getLogger(__name__)

# Global semaphore for connection control - MAX_WORKERS ile uyumlu
GLOBAL_SEMAPHORE = asyncio.Semaphore(MAX_WORKERS)

class FileDownloader:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        self.connector = aiohttp.TCPConnector(
            limit=MAX_WORKERS * 2,  # MAX_WORKERS ile uyumlu
            limit_per_host=MAX_WORKERS,  # MAX_WORKERS ile uyumlu
            ttl_dns_cache=300,
            use_dns_cache=True,
            enable_cleanup_closed=True,
            force_close=True
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://commoncrawl.org/'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=self.connector,
            headers=self.headers
        )
        logger.debug("FileDownloader session başlatıldı")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
        logger.debug("FileDownloader session kapatıldı")
    
    async def download_gzip_file(self, path: str) -> Optional[str]:
        """Tek gzip dosyasını indir ve içeriğini döndür"""
        url = f"{COMMONCRAWL_BASE_URL}{path}"
        
        for attempt in range(MAX_RETRIES):
            try:
                async with GLOBAL_SEMAPHORE:
                    logger.debug(f"İndiriliyor: {path} (deneme {attempt + 1}/{MAX_RETRIES})")
                    
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            logger.debug(f"Başarılı: {path} ({len(content)} bytes)")
                            
                            # Gzip decompress
                            try:
                                decompressed = gzip.decompress(content)
                                text_content = decompressed.decode('utf-8', errors='ignore')
                                logger.debug(f"Decompress başarılı: {path} ({len(text_content)} karakter)")
                                return text_content
                            except Exception as e:
                                logger.error(f"Decompress hatası {path}: {e}")
                                return None
                        else:
                            logger.warning(f"HTTP {response.status}: {path}")
                            if response.status == 403:
                                logger.error(f"403 Forbidden: {path}")
                                raise Exception(f"403 Forbidden: {path}")
                            return None
                            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout hatası {path} (deneme {attempt + 1})")
            except Exception as e:
                logger.warning(f"İndirme hatası {path} (deneme {attempt + 1}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
        
        logger.error(f"Tüm denemeler başarısız: {path}")
        return None
    
    async def download_batch(self, paths: List[str]) -> List[Tuple[str, Optional[str]]]:
        """Birden fazla dosyayı paralel indir"""
        logger.info(f"Batch indiriliyor: {len(paths)} dosya")
        
        tasks = []
        for path in paths:
            task = asyncio.create_task(self.download_gzip_file(path))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sonuçları işle
        processed_results = []
        success_count = 0
        
        for i, result in enumerate(results):
            path = paths[i]
            if isinstance(result, Exception):
                logger.error(f"Task hatası {path}: {result}")
                processed_results.append((path, None))
            else:
                if result:
                    success_count += 1
                    logger.debug(f"Batch başarılı: {path}")
                processed_results.append((path, result))
        
        logger.info(f"Batch tamamlandı: {success_count}/{len(paths)} başarılı")
        return processed_results 