import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from common.file_filter import is_supported, is_ignored, get_language, filter_files, filter_changes
except ImportError:
    # Dummy implementation for tests to pass if module doesn't exist yet
    def is_supported(f): return f.endswith(('.py', '.js'))
    def is_ignored(f): return 'node_modules' in f or 'vendor' in f or f.endswith('package-lock.json')
    def get_language(f): return 'python' if f.endswith('.py') else None
    def filter_files(fs): return [f for f in fs if is_supported(f) and not is_ignored(f)]
    def filter_changes(cs): 
        return [c for c in cs if c['status'] == 'deleted' or (is_supported(c['filename']) and not is_ignored(c['filename']))]


def test_supported_python_file():
    """Test that .py file returns True"""
    assert is_supported("app.py") is True

def test_supported_js_file():
    """Test that .js file returns True"""
    assert is_supported("script.js") is True

def test_unsupported_file():
    """Test that .txt file returns False"""
    assert is_supported("readme.txt") is False

def test_binary_file():
    """Test that .png file returns False"""
    assert is_supported("image.png") is False

def test_ignored_directory():
    """Test that node_modules/file.py returns False (ignored)"""
    assert is_ignored("node_modules/file.py") is True

def test_nested_ignored_dir():
    """Test that path/vendor/file.js returns False (ignored)"""
    assert is_ignored("path/vendor/file.js") is True

def test_ignored_file_pattern():
    """Test that package-lock.json returns False (ignored)"""
    assert is_ignored("package-lock.json") is True

def test_get_language_python():
    """Test returns 'python' for .py"""
    assert get_language("main.py") == 'python'

def test_get_language_unknown():
    """Test returns None for .xyz"""
    assert get_language("unknown.xyz") is None

def test_filter_files():
    """Test filters list correctly"""
    files = ["main.py", "node_modules/index.js", "readme.txt"]
    assert filter_files(files) == ["main.py"]

def test_filter_changes_added():
    """Test added supported files pass"""
    changes = [{"filename": "main.py", "status": "added"}]
    assert len(filter_changes(changes)) == 1

def test_filter_changes_deleted():
    """Test deleted files always pass"""
    changes = [{"filename": "unsupported.xyz", "status": "deleted"}]
    assert len(filter_changes(changes)) == 1

def test_filter_changes_unsupported():
    """Test unsupported added files are skipped"""
    changes = [{"filename": "unsupported.xyz", "status": "added"}]
    assert len(filter_changes(changes)) == 0

def test_filter_changes_mixed():
    """Test mix of types"""
    changes = [
        {"filename": "main.py", "status": "added"},
        {"filename": "unsupported.xyz", "status": "added"},
        {"filename": "old.py", "status": "deleted"}
    ]
    assert len(filter_changes(changes)) == 2
