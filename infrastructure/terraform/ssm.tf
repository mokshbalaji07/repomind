resource "aws_ssm_parameter" "gemini_api_key" {
  name        = "/repomind/prod/gemini-api-key"
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_MANUALLY"
  description = "Gemini API key for RepoMind"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_ssm_parameter" "github_token" {
  name        = "/repomind/prod/github-token"
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_MANUALLY"
  description = "GitHub PAT for RepoMind private repo access"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = var.project_name
  }
}
