"""Configuration module for RepoMind.

All configuration is driven by environment variables with sensible defaults.
Secrets are NEVER stored here — they are retrieved from SSM at runtime.
"""
import os

# --- AWS ---
AWS_REGION = os.environ.get('AWS_REGION_OVERRIDE', os.environ.get('AWS_REGION', 'ap-south-1'))

# --- S3 ---
S3_BUCKET = os.environ.get('REPOMIND_S3_BUCKET', 'repomind-vectors-736486261162')
S3_PREFIX_PERFILE = 'embeddings/per-file'
S3_PREFIX_INDEX = 'embeddings/index'

# --- DynamoDB ---
DYNAMODB_TABLE = os.environ.get('REPOMIND_DYNAMODB_TABLE', 'repomind-state')

# --- Gemini Models (NOT secrets) ---
GEMINI_EMBEDDING_MODEL = os.environ.get('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001')
GEMINI_ANSWER_MODEL = os.environ.get('GEMINI_ANSWER_MODEL', 'gemini-3.1-flash-lite')

# --- SSM Parameter Names (NOT the values) ---
GEMINI_API_KEY_SSM_PARAM = os.environ.get('GEMINI_API_KEY_SSM_PARAM', '/repomind/prod/gemini-api-key')
GITHUB_TOKEN_SSM_PARAM = os.environ.get('GITHUB_TOKEN_SSM_PARAM', '/repomind/prod/github-token')

# --- Embedding Tuning ---
EMBEDDING_DIMENSION = 768
EMBEDDING_MAX_CONCURRENCY = int(os.environ.get('EMBEDDING_MAX_CONCURRENCY', '5'))
EMBEDDING_MAX_RETRIES = int(os.environ.get('EMBEDDING_MAX_RETRIES', '3'))
EMBEDDING_RPM_LIMIT = int(os.environ.get('EMBEDDING_RPM_LIMIT', '1500'))

# --- Answer Model Tuning ---
ANSWER_RPM_LIMIT = int(os.environ.get('ANSWER_RPM_LIMIT', '30'))
ANSWER_MAX_RETRIES = int(os.environ.get('ANSWER_MAX_RETRIES', '3'))

# --- Query ---
TOP_K = int(os.environ.get('REPOMIND_TOP_K', '5'))
MAX_REQUEST_SIZE = int(os.environ.get('REPOMIND_MAX_REQUEST_SIZE', '10240'))

# --- File Processing ---
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
FALLBACK_CHUNK_MAX_LINES = 100

# --- Supported Languages ---
SUPPORTED_EXTENSIONS: dict[str, str] = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.go': 'go',
    '.rs': 'rust',
}

# --- Ignored Directories ---
IGNORED_DIRS: set[str] = {
    'node_modules', '.git', 'vendor', 'build', 'dist', '__pycache__',
    '.venv', 'venv', '.tox', 'target', 'bin', 'obj', '.idea', '.vscode',
    '.github', 'coverage', '.mypy_cache', '.pytest_cache',
}

# --- Ignored File Patterns (glob) ---
IGNORED_FILE_PATTERNS: list[str] = [
    'package-lock.json',
    'yarn.lock',
    'poetry.lock',
    'Pipfile.lock',
    'go.sum',
    'Cargo.lock',
    '*.min.js',
    '*.min.css',
    '*.map',
    '*.generated.*',
    '*.pb.go',
    '*_pb2.py',
]
