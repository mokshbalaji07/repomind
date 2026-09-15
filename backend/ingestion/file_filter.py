"""File filtering for the RepoMind ingestion pipeline.

Import paths use `common.*` (no `backend.` prefix) because the Lambda
deployment ZIP has `common/` at its root.
"""
import os
import fnmatch
from typing import List, Tuple, Optional

from common.config import (
    SUPPORTED_EXTENSIONS,
    IGNORED_DIRS,
    MAX_FILE_SIZE,
    IGNORED_FILE_PATTERNS,
)
from common.models import FileChange


def is_supported_file(file_path: str) -> bool:
    """Check if a file should be processed based on extension and path."""
    # Check for ignored directory components
    parts = file_path.replace('\\', '/').split('/')
    for part in parts[:-1]:  # all but the filename
        if part in IGNORED_DIRS:
            return False

    filename = os.path.basename(file_path)

    # Check ignored file patterns
    for pattern in IGNORED_FILE_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return False

    # Check extension
    _, ext = os.path.splitext(filename)
    return ext.lower() in SUPPORTED_EXTENSIONS


def get_language(file_path: str) -> Optional[str]:
    """Return the language name for a file, or None if unsupported."""
    _, ext = os.path.splitext(file_path)
    return SUPPORTED_EXTENSIONS.get(ext.lower())


def filter_files(file_paths: List[str]) -> List[str]:
    """Filter a list of file paths to only supported files."""
    return [fp for fp in file_paths if is_supported_file(fp)]


def filter_changes(
    changes: List[FileChange],
) -> Tuple[List[FileChange], List[FileChange]]:
    """Separate changes into (processable, skipped).

    Deleted files are always processable (need to remove from index).
    Added/modified files are only processable if they pass the filter.
    """
    processable: List[FileChange] = []
    skipped: List[FileChange] = []

    for change in changes:
        if change.change_type == 'deleted':
            processable.append(change)
        elif change.change_type in ('added', 'modified'):
            if is_supported_file(change.file_path):
                processable.append(change)
            else:
                skipped.append(change)
        else:
            skipped.append(change)

    return processable, skipped
