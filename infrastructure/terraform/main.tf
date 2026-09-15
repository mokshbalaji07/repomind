locals {
  function_name_ingestion = "${var.project_name}-ingestion"
  function_name_query     = "${var.project_name}-query"
  s3_bucket_name          = "${var.project_name}-vectors-${var.aws_account_id}"
  dynamodb_table_name     = "${var.project_name}-state"
  state_machine_name      = "${var.project_name}-ingestion-workflow"
}
