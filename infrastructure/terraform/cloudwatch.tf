resource "aws_cloudwatch_log_group" "lambda_ingestion" {
  name              = "/aws/lambda/${local.function_name_ingestion}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "lambda_query" {
  name              = "/aws/lambda/${local.function_name_query}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${local.state_machine_name}"
  retention_in_days = var.log_retention_days
}
