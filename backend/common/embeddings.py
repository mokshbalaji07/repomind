import json
import time
import logging
import urllib.request
import urllib.error
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config
from .models import CodeChunk
from .logger import mask

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rpm: int):
        self.rpm = rpm
        self.interval = 60.0 / rpm
        self.last_request = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_request
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_request = time.time()

class GeminiEmbeddingClient:
    def __init__(self, api_key: str, model: str = config.GEMINI_EMBEDDING_MODEL):
        self.api_key = api_key
        self.model = model
        self.rate_limiter = RateLimiter(config.EMBEDDING_RPM_LIMIT)

    def _call_api(self, text: str, task_type: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        data = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        retries = 0
        backoff = 1.0
        while retries <= config.EMBEDDING_MAX_RETRIES:
            self.rate_limiter.wait()
            try:
                with urllib.request.urlopen(req) as response:
                    body = response.read()
                    res_json = json.loads(body)
                    embedding = res_json.get('embedding', {}).get('values', [])
                    if not embedding or len(embedding) != config.EMBEDDING_DIMENSION:
                        raise ValueError(f"Invalid embedding dimensions, expected {config.EMBEDDING_DIMENSION}")
                    return embedding
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503) and retries < config.EMBEDDING_MAX_RETRIES:
                    retries += 1
                    retry_after = e.headers.get('Retry-After')
                    sleep_time = float(retry_after) if retry_after else backoff
                    time.sleep(sleep_time)
                    backoff *= 2
                else:
                    logger.error(f"HTTP Error {e.code}: {e.reason}")
                    raise
            except Exception as e:
                if retries < config.EMBEDDING_MAX_RETRIES:
                    retries += 1
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"Error calling embedding API: {str(e)}")
                    raise
        raise Exception("Max retries exceeded")

    def embed_text(self, text: str, task_type: str = 'RETRIEVAL_DOCUMENT') -> List[float]:
        return self._call_api(text, task_type)

    def embed_query(self, query: str) -> List[float]:
        return self._call_api(query, 'RETRIEVAL_QUERY')

    def embed_chunks(self, chunks: List[CodeChunk]) -> List[Tuple[CodeChunk, List[float]]]:
        results = []
        with ThreadPoolExecutor(max_workers=config.EMBEDDING_MAX_CONCURRENCY) as executor:
            future_to_chunk = {
                executor.submit(self.embed_text, chunk.content, 'RETRIEVAL_DOCUMENT'): chunk
                for chunk in chunks
            }
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    embedding = future.result()
                    results.append((chunk, embedding))
                except Exception as e:
                    logger.error(f"Failed to embed chunk {chunk.chunk_id}: {str(e)}")
        return results
