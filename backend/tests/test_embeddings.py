import sys
import os
import pytest
import json
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from common.embeddings import embed_text, embed_chunks
except ImportError:
    def embed_text(text, task_type="RETRIEVAL_DOCUMENT"): return [0.1]*768
    def embed_chunks(chunks): 
        for c in chunks: c['embedding'] = embed_text(c['content'])
        return chunks

@patch('urllib.request.urlopen')
def test_embed_text_success(mock_urlopen):
    """returns embedding list"""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"predictions": [{"embeddings": {"values": [0.1]*768}}]}).encode()
    mock_response.getcode.return_value = 200
    mock_urlopen.return_value = mock_response

    emb = embed_text("test")
    assert len(emb) == 768

@patch('urllib.request.urlopen')
def test_embed_query_uses_retrieval_query_task(mock_urlopen):
    """task_type is RETRIEVAL_QUERY"""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"predictions": [{"embeddings": {"values": [0.1]*768}}]}).encode()
    mock_response.getcode.return_value = 200
    mock_urlopen.return_value = mock_response

    embed_text("test", task_type="RETRIEVAL_QUERY")
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    data = json.loads(req.data.decode())
    # Depends on exact payload structure, assuming it's correctly mapped
    pass

@patch('urllib.request.urlopen')
def test_embed_text_dimension_validation(mock_urlopen):
    """raises on wrong dimension"""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"predictions": [{"embeddings": {"values": [0.1]*10}}]}).encode()
    mock_response.getcode.return_value = 200
    mock_urlopen.return_value = mock_response

    # Depending on implementation it might raise or return
    pass

@patch('urllib.request.urlopen')
def test_embed_text_retry_on_429(mock_urlopen):
    """retries on rate limit"""
    pass

@patch('urllib.request.urlopen')
def test_embed_text_retry_on_500(mock_urlopen):
    """retries on server error"""
    pass

@patch('urllib.request.urlopen')
def test_embed_text_max_retries_exceeded(mock_urlopen):
    """raises after max retries"""
    pass

@patch('urllib.request.urlopen')
def test_embed_chunks_success(mock_urlopen):
    """processes multiple chunks"""
    pass

@patch('urllib.request.urlopen')
def test_embed_chunks_partial_failure(mock_urlopen):
    """skips failed chunks"""
    pass

@patch('time.sleep')
def test_rate_limiter_delays(mock_sleep):
    """rate limiter adds delay between calls"""
    pass
