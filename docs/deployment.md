# Deployment Guide

## 1. Prerequisites
Ensure you have the following installed and configured on your local machine:
- AWS CLI (authenticated to your account)
- Terraform (v1.5+)
- Python 3.12+
- GitHub CLI (optional, but helpful)

## 2. Secret Setup
Before running Terraform, manually populate the required secrets in AWS Systems Manager Parameter Store.
Run these commands in your terminal (replace `YOUR_KEY` and `YOUR_TOKEN`):

```bash
aws ssm put-parameter \
    --name "/repomind/prod/gemini-api-key" \
    --value "YOUR_KEY" \
    --type "SecureString" \
    --region "ap-south-1"

aws ssm put-parameter \
    --name "/repomind/prod/github-token" \
    --value "YOUR_TOKEN" \
    --type "SecureString" \
    --region "ap-south-1"
```

## 3. Lambda Packaging
Package the Lambda functions into `.zip` files before applying Terraform. 
Run the provided PowerShell script from the project root:

```powershell
.\scripts\package_lambda.ps1
```

## 4. Terraform Workflow
Navigate to the `infrastructure/` directory (or wherever your `.tf` files reside) and execute:

```bash
terraform init
terraform fmt
terraform validate
terraform plan
```
Carefully review the output of `terraform plan`. Ensure it is not attempting to overwrite your SSM parameter values.

```bash
terraform apply
```
Approve the apply when prompted.

## 5. Post-Deployment
After a successful `terraform apply`, note the outputs:
1. Locate the **Function URL** in the Terraform output.
2. Open `frontend/index.html`.
3. In the UI Configuration section, paste the Function URL.
4. Verify via the AWS Console that the Lambda functions, S3 buckets, DynamoDB table, and Step Functions State Machine were created successfully.

## 6. GitHub Actions Setup
The AWS infrastructure for GitHub OIDC is configured by Terraform. Ensure your `.github/workflows/ingest.yml` file is configured with the correct AWS region (`ap-south-1`) and IAM Role ARN (from Terraform output).

## 7. First Ingestion
1. Push code to the target repository's `main` branch.
2. GitHub Actions will trigger.
3. Monitor the Actions tab in GitHub. It will invoke the AWS Step Functions state machine.
4. Open the AWS Console -> Step Functions to monitor the visual execution graph.

## 8. Frontend Deployment
The frontend is a simple static application.
1. Simply open `frontend/index.html` in your local web browser.
2. Ensure the Function URL is set.
3. Enter `owner/repo` and start asking questions!
