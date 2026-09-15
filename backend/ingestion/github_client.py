"""GitHub REST API client using urllib.request.

Supports both authenticated and unauthenticated access:
- Public repos: works without a token (but authenticated is preferred for
  higher rate limits)
- Private repos: requires a valid token

Import paths use `common.*` for Lambda compatibility.
"""
import json
import time
import logging
import urllib.request
import urllib.error
from typing import List, Tuple, Optional, Any

from common.models import FileChange
from common.config import MAX_FILE_SIZE

logger = logging.getLogger(__name__)


# ---------- Exceptions ----------

class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API HTTP {status_code}: {message}")


class GitHubRateLimitError(GitHubAPIError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(403, f"Rate limit exceeded. Retry after {retry_after}s")


class GitHubAuthError(GitHubAPIError):
    pass


class GitHubNotFoundError(GitHubAPIError):
    pass


# ---------- Client ----------

class GitHubClient:
    """Lightweight GitHub REST API client."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = 'https://api.github.com'

    def _request(
        self,
        path: str,
        accept: str = 'application/vnd.github+json',
    ) -> Any:
        """Make an HTTP request to the GitHub API with retries."""
        url = path if path.startswith('http') else f"{self.base_url}{path}"
        headers = {
            'Accept': accept,
            'User-Agent': 'RepoMind/1.0',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        max_retries = 3
        for attempt in range(max_retries):
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    # Return raw bytes for raw-content requests
                    if accept == 'application/vnd.github.raw+json':
                        return raw
                    return json.loads(raw.decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    raise GitHubAuthError(401, 'Authentication failed')
                if e.code == 403:
                    remaining = e.headers.get('X-RateLimit-Remaining', '')
                    if remaining == '0':
                        reset_ts = int(e.headers.get('X-RateLimit-Reset', '0'))
                        retry_after = max(1, reset_ts - int(time.time()))
                        raise GitHubRateLimitError(retry_after)
                    raise GitHubAPIError(403, 'Forbidden')
                if e.code == 404:
                    raise GitHubNotFoundError(404, 'Not Found')
                if e.code >= 500 and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise GitHubAPIError(e.code, str(e.reason))
            except urllib.error.URLError as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise GitHubAPIError(0, f"Network error: {e.reason}")

    # ---------- Public API ----------

    def get_compare(self, repo: str, base: str, head: str) -> List[FileChange]:
        """Compare two commits and return file changes."""
        data = self._request(f'/repos/{repo}/compare/{base}...{head}')
        changes: List[FileChange] = []

        for f in data.get('files', []):
            status = f.get('status', '')
            if status == 'removed':
                change_type = 'deleted'
            elif status == 'renamed':
                change_type = 'modified'
            elif status in ('added', 'modified'):
                change_type = status
            else:
                change_type = 'modified'  # safe default

            changes.append(FileChange(
                file_path=f['filename'],
                change_type=change_type,
            ))
        return changes

    def get_tree(self, repo: str, sha: str) -> List[str]:
        """Get all file paths in a repository tree (for initial ingestion)."""
        data = self._request(f'/repos/{repo}/git/trees/{sha}?recursive=1')
        return [
            item['path']
            for item in data.get('tree', [])
            if item.get('type') == 'blob'
        ]

    def get_file_content(
        self, repo: str, file_path: str, ref: str,
    ) -> Tuple[str, int]:
        """Fetch a single file's content. Returns (content, size)."""
        try:
            # First get metadata to check size
            meta = self._request(f'/repos/{repo}/contents/{file_path}?ref={ref}')
            if isinstance(meta, list) or meta.get('type') != 'file':
                return '', 0

            size = meta.get('size', 0)
            if size > MAX_FILE_SIZE:
                logger.info(f"Skipping {file_path}: size {size} > {MAX_FILE_SIZE}")
                return '', 0

            # Fetch raw content
            raw = self._request(
                f'/repos/{repo}/contents/{file_path}?ref={ref}',
                accept='application/vnd.github.raw+json',
            )
            if isinstance(raw, bytes):
                try:
                    return raw.decode('utf-8'), size
                except UnicodeDecodeError:
                    return '', 0  # Binary file
            return str(raw), size

        except GitHubNotFoundError:
            return '', 0
        except Exception as e:
            logger.error(f"Failed to fetch {file_path}: {e}")
            return '', 0

    def validate_repo_access(self, repo: str) -> bool:
        """Check whether the client can access a repository."""
        try:
            self._request(f'/repos/{repo}')
            return True
        except GitHubAPIError:
            return False
