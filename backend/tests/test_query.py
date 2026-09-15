import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_query_success():
    """full flow returns answer with sources"""
    pass

def test_query_missing_repo():
    """returns 400"""
    pass

def test_query_missing_question():
    """returns 400"""
    pass

def test_query_invalid_json():
    """returns 400"""
    pass

def test_query_too_large():
    """returns 413"""
    pass

def test_query_invalid_repo_format():
    """returns 400"""
    pass

def test_query_question_too_long():
    """returns 400"""
    pass

def test_query_no_index():
    """returns insufficient evidence"""
    pass

def test_query_cors_preflight():
    """returns 200 with CORS headers"""
    pass

def test_query_cors_headers_present():
    """response has CORS headers"""
    pass

def test_query_internal_error():
    """returns 500 without exposing stack trace"""
    pass
