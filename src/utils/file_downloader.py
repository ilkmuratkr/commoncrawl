import asyncio
import aiohttp
import gzip
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from config.settings import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, COMMONCRAWL_BASE_URL

logger = logging.getLogger(__name__)

class FileDownloader:
    """CommonCrawl dosyalarını indiren ve işleyen sınıf"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def download_gzip_file(self, path: str) -> Optional[str]:
        """Gzip dosyasını indir ve içeriğini döndür"""
        url = f"{COMMONCRAWL_BASE_URL}{path}"
        
        for attempt in range(MAX_RETRIES):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Gzip dosyasını aç
                        try:
                            decompressed = gzip.decompress(content)
                            return decompressed.decode('utf-8', errors='ignore')
                        except Exception as e:
                            logger.warning(f"Gzip açma hatası {url}: {e}")
                            return None
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except Exception as e:
                logger.warning(f"İndirme hatası {url} (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    
        return None
    
    async def download_batch(self, paths: List[str]) -> List[Tuple[str, Optional[str]]]:
        """Birden fazla dosyayı paralel indir"""
        tasks = []
        for path in paths:
            task = asyncio.create_task(self.download_gzip_file(path))
            tasks.append((path, task))
        
        results = []
        for path, task in tasks:
            try:
                content = await task
                results.append((path, content))
            except Exception as e:
                logger.error(f"Task hatası {path}: {e}")
                results.append((path, None))
                
        return results 