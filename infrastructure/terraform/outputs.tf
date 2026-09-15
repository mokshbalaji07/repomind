output "query_function_url" {
  value = aws_lambda_function_url.query.function_url
}

output "ingestion_lambda_arn" {
  value = aws_lambda_function.ingestion.arn
}

output "query_lambda_arn" {
  value = aws_lambda_function.query.arn
}

output "state_machine_arn" {
  value = aws_sfn_state_machine.ingestion.arn
}

output "s3_bucket_name" {
  value = aws_s3_bucket.vectors.id
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.state.name
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github.arn
}
