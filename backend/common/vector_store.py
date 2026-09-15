import io
import json
import logging
import urllib.parse
from typing import List, Tuple
import numpy as np
import boto3

from . import config
from .models import CodeChunk

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, bucket: str = config.S3_BUCKET, region: str = config.AWS_REGION):
        self.bucket = bucket
        self.s3 = boto3.client('s3', region_name=region)

    def _safe_path(self, repo: str, file_path: str = None) -> str:
        safe_repo = urllib.parse.quote(repo.replace('/', '_'), safe='')
        if file_path:
            return f"{safe_repo}/{file_path}"
        return safe_repo

    def save_file_embeddings(self, repo: str, file_path: str, chunks: List[CodeChunk], embeddings: List[List[float]]) -> str:
        if not chunks or not embeddings:
            return ""

        safe_repo = self._safe_path(repo)
        s3_key = f"{config.S3_PREFIX_PERFILE}/{safe_repo}/{file_path}.npz"
        
        metadata = [c.to_dict() for c in chunks]
        embeddings_arr = np.array(embeddings, dtype=np.float32)

        buffer = io.BytesIO()
        np.savez_compressed(buffer, embeddings=embeddings_arr, metadata=json.dumps(metadata))
        buffer.seek(0)

        self.s3.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=buffer.getvalue()
        )
        return s3_key

    def delete_file_embeddings(self, repo: str, file_path: str):
        safe_repo = self._safe_path(repo)
        s3_key = f"{config.S3_PREFIX_PERFILE}/{safe_repo}/{file_path}.npz"
        self.s3.delete_object(Bucket=self.bucket, Key=s3_key)

    def rebuild_consolidated_index(self, repo: str) -> int:
        safe_repo = self._safe_path(repo)
        prefix = f"{config.S3_PREFIX_PERFILE}/{safe_repo}/"
        
        paginator = self.s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
        
        all_embeddings = []
        all_metadata = []

        for page in pages:
            if 'Contents' not in page:
                continue
            for obj in page['Contents']:
                s3_key = obj['Key']
                try:
                    response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
                    buffer = io.BytesIO(response['Body'].read())
                    with np.load(buffer, allow_pickle=True) as data:
                        all_embeddings.append(data['embeddings'])
                        all_metadata.extend(json.loads(data['metadata'].item()))
                except Exception as e:
                    logger.error(f"Failed to load {s3_key}: {e}")

        if not all_embeddings:
            return 0

        final_embeddings = np.concatenate(all_embeddings, axis=0)
        
        index_key = f"{config.S3_PREFIX_INDEX}/{safe_repo}/index.npz"
        buffer = io.BytesIO()
        np.savez_compressed(buffer, embeddings=final_embeddings, metadata=json.dumps(all_metadata))
        buffer.seek(0)
        
        self.s3.put_object(Bucket=self.bucket, Key=index_key, Body=buffer.getvalue())
        return len(final_embeddings)

    def load_index(self, repo: str) -> Tuple[np.ndarray, List[dict]]:
        safe_repo = self._safe_path(repo)
        index_key = f"{config.S3_PREFIX_INDEX}/{safe_repo}/index.npz"
        
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=index_key)
            buffer = io.BytesIO(response['Body'].read())
            with np.load(buffer, allow_pickle=True) as data:
                return data['embeddings'], json.loads(data['metadata'].item())
        except self.s3.exceptions.NoSuchKey:
            return np.array([]), []
        except Exception as e:
            logger.error(f"Failed to load index for {repo}: {e}")
            return np.array([]), []

    def search(self, query_embedding: List[float], embeddings: np.ndarray, metadata: List[dict], top_k: int = config.TOP_K) -> List[Tuple[dict, float]]:
        if len(embeddings) == 0:
            return []
            
        q = np.array(query_embedding, dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(q)
        norms[norms == 0] = 1.0
        scores = np.dot(embeddings, q) / norms
        
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append((metadata[idx], float(scores[idx])))
            
        return results
