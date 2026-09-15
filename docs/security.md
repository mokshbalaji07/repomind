# Security Design

## 1. Secret Management
- Secrets are stored using AWS Systems Manager (SSM) Parameter Store using the Standard tier `SecureString` type.
- Encrypted at rest using AWS managed KMS key (`alias/aws/ssm`).
- Two parameters are used:
  - `/repomind/prod/gemini-api-key`
  - `/repomind/prod/github-token`
- **Terraform Integration:** Terraform manages the *metadata* of these parameters but NOT the actual secret values. The `lifecycle { ignore_changes = [value] }` block ensures that `terraform plan` or `apply` doesn't overwrite real secrets.
- Secrets are manually populated via the AWS CLI.
- **Zero Exposure:** Secrets are NEVER checked into Git, source code, Terraform state files, application logs, frontend code, or GitHub Actions definitions.

## 2. IAM Least Privilege
- Every Lambda function runs with a dedicated, custom IAM role containing only the exact permissions needed.
- The Step Functions execution role is restricted strictly to invoking the specific ingestion Lambda functions.
- The GitHub Actions OIDC role is constrained by conditions (e.g., `StringLike` on `token.actions.githubusercontent.com:sub`) to only allow actions from the specific repository.

## 3. GitHub OIDC Federation
- Long-lived AWS access keys (Access Key ID and Secret Access Key) are NOT used.
- GitHub Actions authenticate to AWS via OpenID Connect (OIDC).
- The Trust Policy is scoped down. Example condition: `repo:mokshbalaji07/repomind:*`.

## 4. Lambda Function URL Security
- `AUTH_TYPE = NONE` is used. This is intentional for a public college demo to avoid complex client-side authentication flows.
- To mitigate abuse, the Lambda code implements:
  - Strict input validation.
  - Request size limits.
  - CORS configuration restricting allowed origins.
- *Note: In a production enterprise scenario, `AUTH_TYPE = AWS_IAM` or an API Gateway with Cognito/OAuth would be required.*

## 5. GitHub Token Security
- A Fine-Grained Personal Access Token (PAT) is used by the Ingestion Lambda.
- Granted minimal permissions (Read-only access to Repository Contents).
- Never exposed to the frontend or application logs.

## 6. Security Checklist
- [x] No hardcoded secrets in source code.
- [x] Secrets excluded from Terraform state.
- [x] OIDC used instead of IAM User Access Keys.
- [x] Least privilege IAM roles for all compute resources.
- [x] Function URL CORS restricted.
- [x] Input sanitization in Lambda.
