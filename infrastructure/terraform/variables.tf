variable "aws_region" {
  type        = string
  default     = "ap-south-1"
  description = "AWS region"
}

variable "aws_account_id" {
  type        = string
  default     = "736486261162"
  description = "AWS Account ID"
}

variable "project_name" {
  type        = string
  default     = "repomind"
  description = "Project name"
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Environment name"
}

variable "github_repo" {
  type        = string
  default     = "mokshbalaji07/repomind"
  description = "GitHub repository"
}

variable "github_org" {
  type        = string
  default     = "mokshbalaji07"
  description = "GitHub organization"
}

variable "lambda_runtime" {
  type        = string
  default     = "python3.13"
  description = "Lambda runtime"
}

variable "dynamodb_read_capacity" {
  type        = number
  default     = 5
  description = "DynamoDB read capacity"
}

variable "dynamodb_write_capacity" {
  type        = number
  default     = 5
  description = "DynamoDB write capacity"
}

variable "log_retention_days" {
  type        = number
  default     = 14
  description = "CloudWatch log retention in days"
}

variable "gemini_embedding_model" {
  type        = string
  default     = "gemini-embedding-001"
  description = "Gemini embedding model name"
}

variable "gemini_answer_model" {
  type        = string
  default     = "gemini-3.1-flash-lite"
  description = "Gemini answer model name"
}
