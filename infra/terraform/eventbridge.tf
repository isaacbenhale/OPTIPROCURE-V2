# =====================================================================
# EventBridge Scheduler — déclenche le batch de publication quotidien
# (CLAUDE.md §"Deux workflows à maintenir" §8.1)
# =====================================================================

resource "aws_scheduler_schedule_group" "publication" {
  name = "${local.name_prefix}-publication"
}

resource "aws_iam_role" "eventbridge_scheduler" {
  name = "${local.name_prefix}-scheduler-invoke-publication"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "eventbridge_scheduler_invoke" {
  name = "${local.name_prefix}-scheduler-invoke-policy"
  role = aws_iam_role.eventbridge_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.publication_coordinator.arn
    }]
  })
}

resource "aws_scheduler_schedule" "daily_publication_batch" {
  name       = "${local.name_prefix}-daily-publication-batch"
  group_name = aws_scheduler_schedule_group.publication.name

  schedule_expression = var.publication_batch_schedule

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.publication_coordinator.arn
    role_arn = aws_iam_role.eventbridge_scheduler.arn

    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}

resource "aws_lambda_permission" "scheduler_invoke_publication" {
  statement_id  = "AllowEventBridgeSchedulerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.publication_coordinator.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.daily_publication_batch.arn
}
