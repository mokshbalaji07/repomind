# API Documentation

## Endpoint
**Lambda Function URL** (Generated post-deployment, e.g., `https://<id>.lambda-url.ap-south-1.on.aws/`)

## Details
- **Method:** `POST`
- **Authentication:** None (Public Endpoint)
- **Content-Type:** `application/json`
- **CORS:** Configured to allow all origins (`*`) for demo purposes.

## Request Payload

```json
{
  "repo": "owner/repository",
  "question": "Where is user authentication implemented?"
}
```

### Validation Rules
- `repo`: Must be in the format `owner/repo`. Max length 100 characters.
- `question`: Cannot be empty. Max length 1000 characters.
- Request Body Size: Limited by Lambda API Gateway/Function URL payload limits (typically 6MB).

## Response Payload

### Success (200 OK)

```json
{
  "answer": "Based on the repository code, user authentication is primarily handled in the `login.py` file using the `authenticate_user` function...",
  "sources": [
    {
      "file_path": "src/auth/login.py",
      "symbol": "authenticate_user",
      "symbol_type": "function",
      "start_line": 42,
      "end_line": 67,
      "repo": "owner/repository",
      "commit_sha": "abc123def456",
      "relevance_score": 0.89
    }
  ],
  "repo": "owner/repository",
  "question": "Where is user authentication implemented?"
}
```

### Error Responses

**400 Bad Request** (Invalid Input)
```json
{
  "error": "Invalid repository format. Expected 'owner/repo'."
}
```

**413 Payload Too Large**
Returned if the request body exceeds allowed limits.

**500 Internal Server Error**
```json
{
  "error": "Internal server error occurred during processing."
}
```
