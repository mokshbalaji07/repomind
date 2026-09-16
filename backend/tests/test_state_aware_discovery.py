"""Tests for the state-aware initial-indexing discovery logic.

Validates that op_discover_files correctly forces full-repo ingestion
when no consolidated S3 index exists, and correctly falls back to
incremental ingestion when an index already exists.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from importlib import import_module

# Add both backend/ and backend/ingestion/ to sys.path so handler.py
# can resolve its flat imports (common.*, github_client, file_filter)
_backend = os.path.join(os.path.dirname(__file__), '..')
_ingestion = os.path.join(_backend, 'ingestion')
sys.path.insert(0, _backend)
sys.path.insert(0, _ingestion)

# Now import handler as a top-level module
import handler as ingestion_handler


# ---------------------------------------------------------------------------
# 1. Valid before_sha + NO consolidated index → is_initial == True
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_discover_initial_when_no_index_exists(mock_vs_cls, mock_gh_cls, _tok):
    """A valid before_sha should still trigger initial ingestion when no
    consolidated index exists in S3."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.return_value = False       # <-- no index

    mock_gh = mock_gh_cls.return_value
    mock_gh.get_tree.return_value = ['a.py', 'b.py']

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'abc123',
        'before': 'def456',                         # valid SHA
    }
    result = ingestion_handler.op_discover_files(event)

    assert result['is_initial'] is True
    mock_gh.get_tree.assert_called_once_with('owner/repo', 'abc123')
    mock_gh.get_compare.assert_not_called()
    assert len(result['changes']) == 2


# ---------------------------------------------------------------------------
# 2. Valid before_sha + EXISTING consolidated index → is_initial == False
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_discover_incremental_when_index_exists(mock_vs_cls, mock_gh_cls, _tok):
    """With a valid before_sha AND an existing index, the system must use
    incremental (compare-based) discovery."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.return_value = True        # <-- index exists

    mock_gh = mock_gh_cls.return_value
    mock_gh.get_compare.return_value = [
        MagicMock(to_dict=lambda: {'file_path': 'c.py', 'change_type': 'modified'})
    ]

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'abc123',
        'before': 'def456',
    }
    result = ingestion_handler.op_discover_files(event)

    assert result['is_initial'] is False
    mock_gh.get_compare.assert_called_once_with('owner/repo', 'def456', 'abc123')
    mock_gh.get_tree.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Empty before_sha + NO index → is_initial == True
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_discover_initial_empty_before_no_index(mock_vs_cls, mock_gh_cls, _tok):
    """Empty before_sha with no index → initial ingestion."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.return_value = False

    mock_gh = mock_gh_cls.return_value
    mock_gh.get_tree.return_value = ['x.py']

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'abc123',
        'before': '',
    }
    result = ingestion_handler.op_discover_files(event)
    assert result['is_initial'] is True
    mock_gh.get_tree.assert_called_once()


# ---------------------------------------------------------------------------
# 4. Zero SHA + NO index → is_initial == True
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_discover_initial_zero_sha_no_index(mock_vs_cls, mock_gh_cls, _tok):
    """Zero SHA (first push) with no index → initial ingestion."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.return_value = False

    mock_gh = mock_gh_cls.return_value
    mock_gh.get_tree.return_value = ['y.py']

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'abc123',
        'before': '0' * 40,
    }
    result = ingestion_handler.op_discover_files(event)
    assert result['is_initial'] is True
    mock_gh.get_tree.assert_called_once()


# ---------------------------------------------------------------------------
# 5. Existing index + normal before_sha → incremental
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_discover_incremental_normal_flow(mock_vs_cls, mock_gh_cls, _tok):
    """Standard incremental case: index exists, valid before_sha."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.return_value = True

    mock_gh = mock_gh_cls.return_value
    mock_gh.get_compare.return_value = []

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'abc123',
        'before': 'prev123',
    }
    result = ingestion_handler.op_discover_files(event)
    assert result['is_initial'] is False
    mock_gh.get_compare.assert_called_once()
    assert result['changes'] == []


# ---------------------------------------------------------------------------
# 6. Existing index + deleted file → deletion handled normally
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_discover_incremental_with_deletion(mock_vs_cls, mock_gh_cls, _tok):
    """Incremental mode correctly passes through deletions."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.return_value = True

    deleted_change = MagicMock()
    deleted_change.to_dict.return_value = {'file_path': 'old.py', 'change_type': 'deleted'}
    mock_gh = mock_gh_cls.return_value
    mock_gh.get_compare.return_value = [deleted_change]

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'abc123',
        'before': 'prev123',
    }
    result = ingestion_handler.op_discover_files(event)
    assert result['is_initial'] is False
    assert len(result['changes']) == 1
    assert result['changes'][0]['change_type'] == 'deleted'


# ---------------------------------------------------------------------------
# 7. Duplicate commit → idempotency (check_idempotency gate, not discover)
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, 'StateManager')
def test_check_idempotency_blocks_duplicate(mock_sm_cls):
    """If a commit is already processed, op_check_idempotency returns True."""
    mock_sm = mock_sm_cls.return_value
    mock_sm.is_commit_processed.return_value = True

    event = {'repo': 'owner/repo', 'commit_sha': 'abc123'}
    result = ingestion_handler.op_check_idempotency(event)
    assert result['already_processed'] is True


# ---------------------------------------------------------------------------
# 8. S3 unexpected error during index_exists → exception propagated
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_discover_raises_on_unexpected_s3_error(mock_vs_cls, mock_gh_cls, _tok):
    """An unexpected S3 error (e.g. 403 AccessDenied) during index_exists
    must NOT be silently swallowed — it must propagate so the Step Function
    fails visibly instead of doing an unintended full re-index."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.side_effect = Exception("AccessDenied: 403")

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'abc123',
        'before': 'def456',
    }
    with pytest.raises(Exception, match="AccessDenied"):
        ingestion_handler.op_discover_files(event)


# ---------------------------------------------------------------------------
# 9. index_exists returns True → subsequent push does NOT re-index full repo
# ---------------------------------------------------------------------------
@patch.object(ingestion_handler, '_get_github_token', return_value=None)
@patch.object(ingestion_handler, 'GitHubClient')
@patch.object(ingestion_handler, 'VectorStore')
def test_subsequent_push_stays_incremental(mock_vs_cls, mock_gh_cls, _tok):
    """After the initial full index is built, the next push with a valid
    before_sha must NOT trigger another full re-index."""
    mock_vs = mock_vs_cls.return_value
    mock_vs.index_exists.return_value = True   # index was built

    mock_gh = mock_gh_cls.return_value
    mock_gh.get_compare.return_value = [
        MagicMock(to_dict=lambda: {'file_path': 'new.py', 'change_type': 'added'})
    ]

    event = {
        'repo': 'owner/repo',
        'commit_sha': 'second_commit',
        'before': 'first_commit',
    }
    result = ingestion_handler.op_discover_files(event)

    assert result['is_initial'] is False
    mock_gh.get_tree.assert_not_called()
    mock_gh.get_compare.assert_called_once()


# ---------------------------------------------------------------------------
# VectorStore.index_exists unit tests
# ---------------------------------------------------------------------------
@patch('common.vector_store.boto3')
def test_index_exists_returns_true(mock_boto3):
    """head_object succeeds → index exists."""
    from common.vector_store import VectorStore

    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3
    mock_s3.head_object.return_value = {}

    vs = VectorStore()
    assert vs.index_exists('owner/repo') is True
    mock_s3.head_object.assert_called_once()


@patch('common.vector_store.boto3')
def test_index_exists_returns_false_on_404(mock_boto3):
    """head_object raises 404 → index does not exist."""
    from common.vector_store import VectorStore
    from botocore.exceptions import ClientError

    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
    mock_s3.head_object.side_effect = ClientError(error_response, 'HeadObject')
    mock_s3.exceptions.ClientError = ClientError

    vs = VectorStore()
    assert vs.index_exists('owner/repo') is False


@patch('common.vector_store.boto3')
def test_index_exists_raises_on_unexpected_error(mock_boto3):
    """head_object raises a non-404 error → must propagate."""
    from common.vector_store import VectorStore
    from botocore.exceptions import ClientError

    mock_s3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    error_response = {'Error': {'Code': '403', 'Message': 'Forbidden'}}
    mock_s3.head_object.side_effect = ClientError(error_response, 'HeadObject')
    mock_s3.exceptions.ClientError = ClientError

    vs = VectorStore()
    with pytest.raises(ClientError):
        vs.index_exists('owner/repo')
