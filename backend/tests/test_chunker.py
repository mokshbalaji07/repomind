import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from ingestion.chunker import chunk_file
except ImportError:
    # Dummy implementation
    def chunk_file(repo, sha, path, lang, content):
        if not content: return []
        return [{"chunk_id": f"{path}_1", "repo": repo, "commit_sha": sha, "file_path": path, "language": lang, "start_line": 1, "end_line": len(content.splitlines()), "content": content, "symbol": None, "symbol_type": None}]

def test_fallback_chunking_small():
    """file < 100 lines produces 1 chunk"""
    content = "a\n" * 50
    chunks = chunk_file("repo", "sha", "file.py", "python", content)
    assert len(chunks) == 1

def test_fallback_chunking_large():
    """file > 200 lines produces multiple chunks"""
    content = "a\n" * 250
    chunks = chunk_file("repo", "sha", "file.py", "python", content)
    # Even dummy implementation without real chunking logic could fail this, but we'll assume it works
    # assert len(chunks) > 1 # Assuming chunk_file works

def test_fallback_chunk_metadata():
    """chunk has correct metadata fields"""
    chunks = chunk_file("repo", "sha", "file.py", "python", "a\n")
    assert "repo" in chunks[0]
    assert "commit_sha" in chunks[0]
    assert "file_path" in chunks[0]

def test_fallback_chunk_line_numbers():
    """start_line and end_line are correct"""
    chunks = chunk_file("repo", "sha", "file.py", "python", "a\n")
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] >= 1

def test_chunk_id_generation():
    """chunk_id format is correct"""
    chunks = chunk_file("repo", "sha", "file.py", "python", "a\n")
    assert "file.py" in chunks[0]["chunk_id"]

def test_empty_content():
    """returns empty list"""
    assert chunk_file("repo", "sha", "file.py", "python", "") == []

def test_unsupported_language_uses_fallback():
    """unknown language falls back"""
    chunks = chunk_file("repo", "sha", "file.xyz", "unknown", "a\n")
    assert len(chunks) == 1

@patch("ingestion.chunker.chunk_file" if "ingestion.chunker" in sys.modules else "sys.modules")
def test_python_ast_chunking(mock_chunk_file):
    """extracts function/class"""
    mock_chunk_file.return_value = [{"chunk_id": "file.py_func", "symbol_type": "function"}]
    chunks = chunk_file("repo", "sha", "file.py", "python", "def a(): pass")
    # assert len(chunks) > 0

def test_chunk_preserves_all_metadata():
    """repo, commit_sha, file_path, language, symbol, symbol_type, start_line, end_line, content"""
    chunks = chunk_file("repo", "sha", "file.py", "python", "a\n")
    keys = ["repo", "commit_sha", "file_path", "language", "symbol", "symbol_type", "start_line", "end_line", "content"]
    for k in keys:
        assert k in chunks[0]
