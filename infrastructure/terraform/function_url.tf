resource "aws_lambda_function_url" "query" {
  function_name      = aws_lambda_function.query.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}
