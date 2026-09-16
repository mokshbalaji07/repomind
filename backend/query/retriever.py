"""Vector retrieval logic for RepoMind.

This module is a core component of the RAG (Retrieval-Augmented Generation) pipeline.
Loads the consolidated index from S3, computes cosine similarity against
the query embedding, and returns the top-K most relevant chunks to augment the LLM prompt.
"""
from typing import List, Tuple, Dict, Any
import logging
import numpy as np

from common.vector_store import VectorStore
from common.embeddings import GeminiEmbeddingClient
from common.config import TOP_K
from common.logger import get_logger

logger = get_logger('query_retriever')


class Retriever:
    """Retrieves relevant code chunks for a natural-language question."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_client: GeminiEmbeddingClient,
    ):
        self.vector_store = vector_store
        self.embedding_client = embedding_client

    def retrieve(
        self,
        repo: str,
        question: str,
        top_k: int = TOP_K,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Embed the question and find the top-K matching chunks.

        Returns a list of (metadata_dict, similarity_score) tuples,
        sorted by descending relevance.  Returns [] if the index is
        empty or does not exist.
        """
        try:
            # 1. Generate query embedding
            query_embedding = self.embedding_client.embed_query(question)

            # 2. Load consolidated index from S3
            embeddings, metadata = self.vector_store.load_index(repo)
            if len(embeddings) == 0 or not metadata:
                logger.info(f"No index found for repo: {repo}")
                return []

            # 3. Compute cosine similarity and return top-K
            results = self.vector_store.search(
                query_embedding, embeddings, metadata, top_k=top_k,
            )
            return results

        except Exception as e:
            logger.error(
                f"Retrieval failed for {repo}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return []
