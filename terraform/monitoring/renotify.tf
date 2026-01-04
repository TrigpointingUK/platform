# Optional: hourly re-notify if alarms remain ALARM

variable "enable_hourly_renotify" {
  description = "Enable hourly re-notification for persistent alarms"
  type        = bool
  default     = true
}

resource "aws_iam_role" "renotify_role" {
  count = var.enable_hourly_renotify ? 1 : 0
  name  = "${var.project_name}-${var.environment}-renotify-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "renotify_policy" {
  count = var.enable_hourly_renotify ? 1 : 0
  name  = "${var.project_name}-${var.environment}-renotify-inline"
  role  = aws_iam_role.renotify_role[0].id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      { Effect = "Allow", Action = ["cloudwatch:DescribeAlarms"], Resource = "*" },
      { Effect = "Allow", Action = ["sns:Publish"], Resource = aws_sns_topic.alerts.arn },
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" }
    ]
  })
}

data "archive_file" "renotify_zip" {
  count       = var.enable_hourly_renotify ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/scripts/renotify.js"
  output_path = "${path.module}/scripts/renotify.zip"
}

resource "aws_lambda_function" "renotify" {
  count         = var.enable_hourly_renotify ? 1 : 0
  function_name = "${var.project_name}-${var.environment}-renotify"
  role          = aws_iam_role.renotify_role[0].arn
  handler       = "renotify.handler"
  runtime       = "nodejs22.x"
  filename      = data.archive_file.renotify_zip[0].output_path
  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.alerts.arn
    }
  }
}

resource "aws_cloudwatch_event_rule" "renotify_hourly" {
  count               = var.enable_hourly_renotify ? 1 : 0
  name                = "${var.project_name}-${var.environment}-renotify-hourly"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "renotify_target" {
  count = var.enable_hourly_renotify ? 1 : 0
  rule  = aws_cloudwatch_event_rule.renotify_hourly[0].name
  arn   = aws_lambda_function.renotify[0].arn
}

resource "aws_lambda_permission" "renotify_invoke" {
  count         = var.enable_hourly_renotify ? 1 : 0
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.renotify[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.renotify_hourly[0].arn
}
