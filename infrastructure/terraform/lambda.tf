# Lambda function deployment packages.
# The ZIPs must be built BEFORE terraform apply (via scripts/package_lambda.ps1
# or the CI/CD pipeline).  The variables default to the standard output paths.

variable "ingestion_zip" {
  description = "Path to the ingestion Lambda deployment ZIP"
  type        = string
  default     = "../../packages/ingestion.zip"
}

variable "query_zip" {
  description = "Path to the query Lambda deployment ZIP"
  type        = string
  default     = "../../packages/query.zip"
}

# ---------- Ingestion Lambda ----------

resource "aws_lambda_function" "ingestion" {
  function_name = local.function_name_ingestion
  role          = aws_iam_role.ingestion.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 300
  memory_size   = 512

  filename         = var.ingestion_zip
  source_code_hash = fileexists(var.ingestion_zip) ? filebase64sha256(var.ingestion_zip) : null

  environment {
    variables = {
      REPOMIND_S3_BUCKET       = aws_s3_bucket.vectors.id
      REPOMIND_DYNAMODB_TABLE  = aws_dynamodb_table.state.name
      GEMINI_EMBEDDING_MODEL   = var.gemini_embedding_model
      GEMINI_API_KEY_SSM_PARAM = aws_ssm_parameter.gemini_api_key.name
      GITHUB_TOKEN_SSM_PARAM   = aws_ssm_parameter.github_token.name
      AWS_REGION_OVERRIDE      = var.aws_region
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_ingestion]

  tags = {
    Component = "ingestion"
  }
}

# ---------- Query Lambda ----------

resource "aws_lambda_function" "query" {
  function_name = local.function_name_query
  role          = aws_iam_role.query.arn
  handler       = "handler.handler"
  runtime       = var.lambda_runtime
  timeout       = 60
  memory_size   = 256

  filename         = var.query_zip
  source_code_hash = fileexists(var.query_zip) ? filebase64sha256(var.query_zip) : null

  environment {
    variables = {
      REPOMIND_S3_BUCKET       = aws_s3_bucket.vectors.id
      GEMINI_EMBEDDING_MODEL   = var.gemini_embedding_model
      GEMINI_ANSWER_MODEL      = var.gemini_answer_model
      GEMINI_API_KEY_SSM_PARAM = aws_ssm_parameter.gemini_api_key.name
      AWS_REGION_OVERRIDE      = var.aws_region
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_query]

  tags = {
    Component = "query"
  }
}
