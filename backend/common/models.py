"""Data models for RepoMind."""
import dataclasses
from typing import List, Optional


@dataclasses.dataclass
class CodeChunk:
    """A code-aware chunk extracted from a source file."""
    repo: str
    commit_sha: str
    file_path: str
    language: str
    symbol: str
    symbol_type: str  # function, class, method, module, declaration, fallback
    start_line: int
    end_line: int
    content: str
    chunk_id: str = dataclasses.field(init=False)

    def __post_init__(self):
        self.chunk_id = (
            f"{self.file_path}::{self.symbol_type}:{self.symbol}"
            f":{self.start_line}-{self.end_line}"
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CodeChunk':
        data = dict(data)  # don't mutate the original
        data.pop('chunk_id', None)
        return cls(**data)


@dataclasses.dataclass
class FileChange:
    """Represents a file change in a commit."""
    file_path: str
    change_type: str  # added, modified, deleted

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'FileChange':
        return cls(**data)


@dataclasses.dataclass
class SourceReference:
    """A source reference included in a query response."""
    file_path: str
    symbol: str
    symbol_type: str
    start_line: int
    end_line: int
    repo: str = ''
    commit_sha: str = ''
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class QueryRequest:
    """A validated query request."""
    repo: str
    question: str

    def validate(self):
        if not self.repo or not self.repo.strip():
            raise ValueError("repo is required")
        if '/' not in self.repo or len(self.repo.split('/')) != 2:
            raise ValueError("repo must be in owner/name format")
        if not self.question or not self.question.strip():
            raise ValueError("question is required")
        if len(self.question) > 2000:
            raise ValueError("question must be at most 2000 characters")


@dataclasses.dataclass
class QueryResponse:
    """Response from the query pipeline."""
    answer: str
    sources: List[SourceReference]
    repo: str = ''
    question: str = ''

    def to_dict(self) -> dict:
        return {
            'answer': self.answer,
            'sources': [s.to_dict() for s in self.sources],
            'repo': self.repo,
            'question': self.question,
        }


@dataclasses.dataclass
class IngestionJob:
    """Tracks an ingestion job."""
    job_id: str
    repo: str
    commit_sha: str
    status: str
    files_total: int = 0
    files_processed: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    created_at: str = ''
    updated_at: str = ''
    error: Optional[str] = None
