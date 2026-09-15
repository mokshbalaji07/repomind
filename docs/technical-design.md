# Technical Design Document

## 1. Introduction & Problem Statement
Developers spend significant time understanding large, unfamiliar codebases. Existing tools often rely on naive text search. RepoMind solves this by providing a semantic, natural-language Q&A interface over code repositories, powered by AI embeddings and syntax-aware chunking.

## 2. Solution Architecture
A fully serverless AWS pipeline utilizing Step Functions for orchestration, Lambda for compute, S3 for blob/vector storage, and DynamoDB for metadata. It utilizes Google Gemini for both vector embeddings and LLM generation.

## 3. Application Architecture

### Ingestion Pipeline Design
Triggered via OIDC from GitHub Actions. Step Functions coordinates the flow:
1. Fetch diffs to determine modified files.
2. Map state parallelizes chunking and embedding generation for changed files.
3. Merges results into a unified index.

### Query Pipeline Design
A synchronous API via Lambda Function URL. It embeds the query, downloads the index, performs similarity search, and constructs a RAG prompt for Gemini.

## 4. Data Models

### CodeChunk Schema
```json
{
  "id": "uuid",
  "file_path": "src/main.py",
  "symbol": "calculate_tax",
  "symbol_type": "function",
  "start_line": 10,
  "end_line": 25,
  "content": "def calculate_tax(amount): ...",
  "embedding": [0.1, 0.4, -0.2, ...]
}
```

### DynamoDB Design
- Table: `RepoMindMetadata`
- Pattern:
  - `PK: REPO#owner/repo`, `SK: STATE#latest` -> Pipeline execution state
  - `PK: REPO#owner/repo`, `SK: FILE#path` -> File metadata (hash, chunk counts)

### S3 Storage Layout
- `bucket/repo_owner/repo_name/artifacts/file_hash.json`
- `bucket/repo_owner/repo_name/index.npy` (Consolidated vectors)
- `bucket/repo_owner/repo_name/metadata.json` (Consolidated chunk metadata)

## 5. Step Functions State Machine Design
1. **CheckCommit**: Has this commit been processed?
2. **GetDiff**: Identify Add/Modify/Delete files.
3. **MapState**:
   - Extract code.
   - Parse via Tree-sitter.
   - Embed via Gemini.
   - Save artifact.
4. **BuildIndex**: Merge artifacts into `index.npy`.

## 6. Tree-sitter Integration
Tree-sitter provides AST parsing. By writing language-specific queries (e.g., Python `(function_definition)` or `(class_definition)`), the system extracts semantically complete blocks of code, preserving context much better than character-count chunking.

## 7. Embedding Strategy
Using `models/embedding-001` (or equivalent Gemini embedding model). Code content is pre-pended with file path and symbol names to enrich the vector representation.

## 8. Vector Storage & Retrieval
- **Storage:** NumPy arrays serialized to binary (`.npy`) and stored in S3.
- **Retrieval:** The Query Lambda downloads the `.npy` file, loads it into memory, and computes cosine similarity using `np.dot(vectors, query_vector) / (np.linalg.norm(...) * ...)`. Top-K results are sliced. Extremely fast and cost-effective for small-to-medium repositories.

## 9. RAG Prompt Design
The prompt provides the LLM with:
1. The user's question.
2. The relevant code chunks (including file path and line numbers).
3. Strict instructions: "Answer ONLY based on the provided context. If the answer is not present, state that."

## 10. Incremental Indexing Algorithm
By tracking the last indexed commit SHA in DynamoDB, the pipeline uses GitHub's Compare API to find changed files. It only processes files where `status != 'removed'`. Deleted files have their S3 artifacts removed during the Map state.

## 11. Error Handling Strategy
- Step Functions implements `Retry` and `Catch` blocks for API rate limits (GitHub/Gemini).
- Lambda DLQ (Dead Letter Queue) captures unhandled query errors.
- Graceful degradation on unsupported languages (fallback to line chunking).

## 12. Security Design
Refer to `security.md`. Highlights include SSM Parameter Store for secrets and strict IAM roles.

## 13. CI/CD Pipeline
Deployment relies on Terraform for infrastructure and GitHub Actions for continuous ingestion of the target repository. No manual AWS console interaction is required post-initial-setup.
