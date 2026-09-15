# AWS Step Functions STANDARD state machine for the ingestion pipeline.
#
# Flow: InitializeJob → CheckIdempotency → (skip if duplicate) →
#       DiscoverFiles → FilterFiles → ProcessFiles (Map, per-file) →
#       HandleDeletions → RebuildIndex → FinalizeJob
#
# CRITICAL: Map workers write ONLY per-file artifacts to S3.
#           The consolidated index is rebuilt AFTER the Map completes.

resource "aws_sfn_state_machine" "ingestion" {
  name     = local.state_machine_name
  role_arn = aws_iam_role.step_functions.arn
  type     = "STANDARD"

  definition = jsonencode({
    Comment = "RepoMind Ingestion Workflow"
    StartAt = "InitializeJob"
    States = {

      # ---- Stage 1: Create job record ----
      InitializeJob = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation"    = "initialize_job"
          "repo.$"       = "$.repo"
          "commit_sha.$" = "$.commit_sha"
          "ref.$"        = "$.ref"
          "before.$"     = "$.before"
          "after.$"      = "$.after"
        }
        ResultPath = "$.job"
        Next       = "CheckIdempotency"
        Retry = [{
          ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
          IntervalSeconds = 2
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      # ---- Stage 2: Idempotency check ----
      CheckIdempotency = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation"    = "check_idempotency"
          "repo.$"       = "$.repo"
          "commit_sha.$" = "$.commit_sha"
        }
        ResultPath = "$.idempotency"
        Next       = "IsAlreadyProcessed"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      IsAlreadyProcessed = {
        Type = "Choice"
        Choices = [{
          Variable      = "$.idempotency.already_processed"
          BooleanEquals = true
          Next          = "SkipDuplicate"
        }]
        Default = "DiscoverFiles"
      }

      SkipDuplicate = {
        Type    = "Succeed"
        Comment = "Commit already processed — idempotent skip"
      }

      # ---- Stage 3: Discover changed files via GitHub API ----
      DiscoverFiles = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation"    = "discover_files"
          "repo.$"       = "$.repo"
          "commit_sha.$" = "$.commit_sha"
          "before.$"     = "$.before"
        }
        ResultPath = "$.discovery"
        Next       = "FilterFiles"
        Retry = [{
          ErrorEquals     = ["States.ALL"]
          IntervalSeconds = 5
          MaxAttempts     = 2
          BackoffRate     = 2
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      # ---- Stage 4: Filter to supported files ----
      FilterFiles = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation"  = "filter_files"
          "changes.$"  = "$.discovery.changes"
        }
        ResultPath = "$.filtered"
        Next       = "ProcessFiles"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      # ---- Stage 5: Process each file (Map — bounded concurrency) ----
      ProcessFiles = {
        Type           = "Map"
        ItemsPath      = "$.filtered.files_to_process"
        MaxConcurrency = 5
        Parameters = {
          "operation"    = "process_file"
          "repo.$"       = "$.repo"
          "commit_sha.$" = "$.commit_sha"
          "file_path.$"  = "$$.Map.Item.Value.file_path"
          "change_type.$" = "$$.Map.Item.Value.change_type"
        }
        Iterator = {
          StartAt = "ProcessSingleFile"
          States = {
            ProcessSingleFile = {
              Type     = "Task"
              Resource = aws_lambda_function.ingestion.arn
              Retry = [{
                ErrorEquals     = ["States.ALL"]
                IntervalSeconds = 5
                MaxAttempts     = 2
                BackoffRate     = 2
              }]
              End = true
            }
          }
        }
        ResultPath = "$.process_results"
        Next       = "HandleDeletions"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      # ---- Stage 6: Remove deleted file artifacts ----
      HandleDeletions = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation"        = "handle_deletions"
          "repo.$"           = "$.repo"
          "files_to_delete.$" = "$.filtered.files_to_delete"
        }
        ResultPath = "$.deletions"
        Next       = "RebuildIndex"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      # ---- Stage 7: Rebuild consolidated index ----
      RebuildIndex = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation" = "rebuild_index"
          "repo.$"    = "$.repo"
        }
        ResultPath = "$.index"
        Next       = "FinalizeJob"
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      # ---- Stage 8: Mark job complete ----
      FinalizeJob = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation"    = "finalize_job"
          "repo.$"       = "$.repo"
          "commit_sha.$" = "$.commit_sha"
          "job_id.$"     = "$.job.job_id"
        }
        End = true
        Catch = [{
          ErrorEquals = ["States.ALL"]
          ResultPath  = "$.error"
          Next        = "MarkFailed"
        }]
      }

      # ---- Failure handler ----
      MarkFailed = {
        Type     = "Task"
        Resource = aws_lambda_function.ingestion.arn
        Parameters = {
          "operation" = "mark_failed"
          "repo.$"    = "$.repo"
          "job_id.$"  = "$.job.job_id"
          "error.$"   = "$.error"
        }
        End = true
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    level                  = "ERROR"
    include_execution_data = true
  }

  tags = {
    Component = "ingestion"
  }
}
