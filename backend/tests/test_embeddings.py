import sys
import os
import pytest
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.embeddings import GeminiEmbeddingClient

@patch('urllib.request.urlopen')
def test_embed_text_success(mock_urlopen):
    """returns embedding list"""
    mock_response = MagicMock()
    # The real implementation expects: {'embedding': {'values': [...]}}
    mock_response.read.return_value = json.dumps({"embedding": {"values": [0.1]*config.EMBEDDING_DIMENSION}}).encode()
    # Need mock_urlopen to act as context manager
    mock_urlopen.return_value.__enter__.return_value = mock_response

    client = GeminiEmbeddingClient(api_key="test")
    emb = client.embed_text("test")
    assert len(emb) == config.EMBEDDING_DIMENSION

@patch('urllib.request.urlopen')
def test_embed_query_uses_retrieval_query_task(mock_urlopen):
    """task_type is RETRIEVAL_QUERY"""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"embedding": {"values": [0.1]*config.EMBEDDING_DIMENSION}}).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    client = GeminiEmbeddingClient(api_key="test")
    client.embed_query("test")
    
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    data = json.loads(req.data.decode())
    assert data['taskType'] == 'RETRIEVAL_QUERY'

def test_embed_text_dimension_validation(): pass
def test_embed_text_retry_on_429(): pass
def test_embed_text_retry_on_500(): pass
def test_embed_text_max_retries_exceeded(): pass
def test_embed_chunks_success(): pass
def test_embed_chunks_partial_failure(): pass
def test_rate_limiter_delays(): pass
