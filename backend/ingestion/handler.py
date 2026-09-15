"""Ingestion Lambda handler for the RepoMind pipeline.

This single Lambda is invoked by Step Functions with different 'operation'
values. Each operation corresponds to one stage of the ingestion workflow.

Import paths use `common.*` / `ingestion.*` (no `backend.` prefix) because
the Lambda deployment ZIP has `common/` and `ingestion/` at its root.
"""
import json
import uuid
from datetime import datetime, timezone

import boto3

from common.config import (
    AWS_REGION,
    GEMINI_API_KEY_SSM_PARAM,
    GITHUB_TOKEN_SSM_PARAM,
)
from common.models import CodeChunk, FileChange
from common.logger import get_logger
from common.chunker import chunk_file
from common.embeddings import GeminiEmbeddingClient
from common.vector_store import VectorStore
from common.dynamo import StateManager
from ingestion.github_client import GitHubClient
from ingestion.file_filter import filter_changes, is_supported_file, get_language

logger = get_logger('ingestion')

# ---------- SSM secret caching (Lambda warm-start optimisation) ----------
_ssm = None
_gemini_key = None
_github_token = None
_github_token_fetched = False  # distinguish "not fetched" from "fetched but empty"


def _get_ssm():
    global _ssm
    if _ssm is None:
        _ssm = boto3.client('ssm', region_name=AWS_REGION)
    return _ssm


def _get_gemini_key() -> str:
    global _gemini_key
    if _gemini_key is None:
        resp = _get_ssm().get_parameter(
            Name=GEMINI_API_KEY_SSM_PARAM, WithDecryption=True
        )
        _gemini_key = resp['Parameter']['Value']
    return _gemini_key


def _get_github_token():
    """Return the GitHub PAT, or None if unavailable (public-repo mode)."""
    global _github_token, _github_token_fetched
    if not _github_token_fetched:
        try:
            resp = _get_ssm().get_parameter(
                Name=GITHUB_TOKEN_SSM_PARAM, WithDecryption=True
            )
            val = resp['Parameter']['Value']
            # Treat the placeholder as "no real token"
            if val and val != 'PLACEHOLDER_SET_MANUALLY':
                _github_token = val
        except Exception:
            _github_token = None
        _github_token_fetched = True
    return _github_token


# ---------- Operation handlers ----------

def op_initialize_job(event: dict) -> dict:
    """Create a new ingestion job in DynamoDB."""
    repo = event['repo']
    commit_sha = event['commit_sha']
    job_id = str(uuid.uuid4())

    sm = StateManager()
    sm.create_job(repo, job_id, commit_sha)

    logger.info(json.dumps({
        'operation': 'initialize_job', 'repo': repo,
        'commit_sha': commit_sha, 'job_id': job_id,
    }))
    return {**event, 'job_id': job_id}


def op_check_idempotency(event: dict) -> dict:
    """Check whether this commit has already been processed."""
    repo = event['repo']
    commit_sha = event['commit_sha']

    sm = StateManager()
    already = sm.is_commit_processed(repo, commit_sha)

    logger.info(json.dumps({
        'operation': 'check_idempotency', 'repo': repo,
        'commit_sha': commit_sha, 'already_processed': already,
    }))
    return {**event, 'already_processed': already}


def op_discover_files(event: dict) -> dict:
    """Use the GitHub REST API to discover changed files."""
    repo = event['repo']
    commit_sha = event['commit_sha']
    before_sha = event.get('before', '')

    token = _get_github_token()
    client = GitHubClient(token=token)

    changes: list[FileChange] = []
    is_initial = (
        not before_sha
        or before_sha == '0' * 40
    )

    if is_initial:
        file_paths = client.get_tree(repo, commit_sha)
        changes = [FileChange(file_path=fp, change_type='added') for fp in file_paths]
        logger.info(f"Initial ingestion: {len(changes)} files discovered")
    else:
        changes = client.get_compare(repo, before_sha, commit_sha)
        logger.info(f"Incremental ingestion: {len(changes)} changes discovered")

    return {
        **event,
        'changes': [c.to_dict() for c in changes],
        'is_initial': is_initial,
    }


def op_filter_files(event: dict) -> dict:
    """Filter discovered files to processable + deletions."""
    changes_data = event.get('changes', [])
    changes = [FileChange.from_dict(c) for c in changes_data]

    processable, skipped = filter_changes(changes)

    files_to_process = [
        c.to_dict() for c in processable if c.change_type in ('added', 'modified')
    ]
    files_to_delete = [
        c.to_dict() for c in processable if c.change_type == 'deleted'
    ]

    logger.info(json.dumps({
        'operation': 'filter_files',
        'to_process': len(files_to_process),
        'to_delete': len(files_to_delete),
        'skipped': len(skipped),
    }))
    return {
        **event,
        'files_to_process': files_to_process,
        'files_to_delete': files_to_delete,
        'files_skipped': len(skipped),
    }


def op_process_file(event: dict) -> dict:
    """Process a single file: fetch → chunk → embed → store (per-file only).

    Called by the Step Functions Map state. NEVER writes to the consolidated
    index — that happens in `op_rebuild_index` after the Map completes.
    """
    repo = event['repo']
    commit_sha = event['commit_sha']
    file_path = event['file_path']

    try:
        # --- Fetch ---
        token = _get_github_token()
        client = GitHubClient(token=token)
        content, size = client.get_file_content(repo, file_path, commit_sha)
        if not content:
            logger.info(f"Skipped {file_path}: empty, binary, or too large")
            return {'file_path': file_path, 'status': 'skipped', 'reason': 'empty_or_binary'}

        # --- Chunk ---
        language = get_language(file_path) or 'unknown'
        chunks = chunk_file(content, file_path, language, repo, commit_sha)
        if not chunks:
            return {'file_path': file_path, 'status': 'skipped', 'reason': 'no_chunks'}

        # --- Embed ---
        gemini_key = _get_gemini_key()
        embedding_client = GeminiEmbeddingClient(api_key=gemini_key)
        results = embedding_client.embed_chunks(chunks)
        if not results:
            return {'file_path': file_path, 'status': 'failed', 'error': 'all_embeddings_failed'}

        successful_chunks = [r[0] for r in results]
        embeddings = [r[1] for r in results]

        # --- Store per-file artifact ---
        vs = VectorStore()
        s3_key = vs.save_file_embeddings(repo, file_path, successful_chunks, embeddings)

        # --- Update DynamoDB metadata ---
        sm = StateManager()
        sm.upsert_file_metadata(repo, file_path, commit_sha, len(successful_chunks), s3_key)

        logger.info(json.dumps({
            'operation': 'process_file', 'file_path': file_path,
            'chunks': len(successful_chunks), 'status': 'success',
        }))
        return {
            'file_path': file_path,
            'status': 'success',
            'chunk_count': len(successful_chunks),
        }

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        return {'file_path': file_path, 'status': 'failed', 'error': str(e)}


def op_handle_deletions(event: dict) -> dict:
    """Remove per-file S3 artifacts and DynamoDB metadata for deleted files."""
    repo = event['repo']
    files_to_delete = event.get('files_to_delete', [])

    vs = VectorStore()
    sm = StateManager()
    count = 0

    for fd in files_to_delete:
        fp = fd.get('file_path') if isinstance(fd, dict) else fd
        if fp:
            try:
                vs.delete_file_embeddings(repo, fp)
                sm.delete_file_metadata(repo, fp)
                count += 1
            except Exception as e:
                logger.error(f"Failed to delete {fp}: {e}")

    logger.info(f"Deletions completed: {count}")
    return {**event, 'deletions_completed': count}


def op_rebuild_index(event: dict) -> dict:
    """Rebuild the consolidated S3 vector index from per-file artifacts.

    This runs AFTER the Map state completes, so there is no concurrency risk.
    """
    repo = event['repo']
    vs = VectorStore()
    count = vs.rebuild_consolidated_index(repo)
    logger.info(f"Index rebuilt for {repo}: {count} vectors")
    return {**event, 'index_size': count}


def op_finalize_job(event: dict) -> dict:
    """Mark the ingestion job as COMPLETED and record the commit."""
    repo = event['repo']
    job_id = event.get('job_id', '')
    commit_sha = event['commit_sha']

    sm = StateManager()
    if job_id:
        sm.update_job_status(repo, job_id, 'COMPLETED')
    sm.mark_commit_processed(repo, commit_sha, job_id or 'unknown')

    logger.info(json.dumps({
        'operation': 'finalize_job', 'repo': repo,
        'job_id': job_id, 'status': 'COMPLETED',
    }))
    return {**event, 'status': 'COMPLETED'}


def op_mark_failed(event: dict) -> dict:
    """Mark the ingestion job as FAILED."""
    repo = event.get('repo', '')
    job_id = event.get('job_id', '')
    error = event.get('error', event.get('Cause', 'Unknown error'))

    if job_id and repo:
        sm = StateManager()
        sm.update_job_status(repo, job_id, 'FAILED', error=str(error))

    logger.error(json.dumps({
        'operation': 'mark_failed', 'repo': repo,
        'job_id': job_id, 'error': str(error),
    }))
    return {**event, 'status': 'FAILED'}


# ---------- Lambda entry-point ----------

def handler(event, context):
    """Main Lambda handler — routes to operation-specific functions."""
    operation = event.get('operation', '')
    dispatch = {
        'initialize_job': op_initialize_job,
        'check_idempotency': op_check_idempotency,
        'discover_files': op_discover_files,
        'filter_files': op_filter_files,
        'process_file': op_process_file,
        'handle_deletions': op_handle_deletions,
        'rebuild_index': op_rebuild_index,
        'finalize_job': op_finalize_job,
        'mark_failed': op_mark_failed,
    }
    fn = dispatch.get(operation)
    if fn is None:
        raise ValueError(f"Unknown operation: {operation}")
    return fn(event)
