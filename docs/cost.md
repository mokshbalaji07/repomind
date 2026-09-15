# Cost Analysis

## 1. Cost Target
The target monthly operational cost for this project is **$0**.

## 2. Disclaimer
Expected cost is $0 under applicable free-tier allowances for the intended low-volume usage. Actual cost may vary depending on AWS account eligibility, current pricing, repository size, API usage, and free-tier limits. Ensure your AWS account is eligible for the Always Free and 12-Month Free Tier limits.

## 3. Service-by-Service Breakdown

| Service | Free Tier Allowance | Expected Usage | Expected Cost |
| :--- | :--- | :--- | :--- |
| **AWS Lambda** | 1M requests + 400K GB-s / month | ~100 invocations / month | $0 |
| **Step Functions (Standard)** | 4,000 state transitions / month | ~200 transitions / month | $0 |
| **Amazon S3** | 5GB storage, 20K GET, 2K PUT / month | < 100MB, < 100 operations | $0 |
| **DynamoDB** | 25 RCU + 25 WCU provisioned free | 5/5 Provisioned Capacity | $0 |
| **CloudWatch Logs** | 5GB ingestion / month | < 1GB | $0 |
| **SSM Parameter Store** | Standard parameters are free | 2 parameters | $0 |
| **Gemini API** | Free tier for low volume usage | Low volume testing | $0 |

## 4. Cost Decisions

Significant architectural decisions were made specifically to maintain the $0 footprint:
- **SSM instead of Secrets Manager:** AWS Secrets Manager costs ~$0.40 per secret per month. Using SSM Parameter Store (Standard tier) saves this cost entirely while maintaining KMS encryption.
- **S3 + NumPy instead of Managed Vector DB:** Hosted vector databases (Pinecone, managed Qdrant, OpenSearch) have fixed hourly/monthly costs. Downloading a NumPy array from S3 directly into Lambda is virtually free and highly performant for this scale.
- **Lambda Function URL instead of API Gateway:** API Gateway can incur charges and adds complexity. Function URLs are included in standard Lambda billing (which falls under the free tier).
- **No VPC Resources:** No EC2 instances, RDS databases, ECS clusters, or NAT Gateways are used, avoiding hourly charges.

## 5. Cost Risks
- **Large Repositories:** Indexing massive repositories (e.g., Linux kernel) could exceed Lambda timeout/memory limits or S3 free tier storage.
- **High Query Volume:** Excessive public usage of the unsecured Function URL could exceed the 1M requests/month free tier.
- **Gemini Free Tier:** Changes to Google's API pricing model could impact embedding and LLM generation costs.

## 6. Monitoring
An existing AWS Budget alert is configured on the account (set to $5/month) to notify if usage unexpectedly incurs charges. **Do not create redundant billing alarms via Terraform.**
