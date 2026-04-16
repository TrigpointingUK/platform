# Archive Email ECS Scheduled Task
#
# A Fargate task that runs daily at 03:00 UTC to generate and email
# data archives to opted-in users. Uses the same API Docker image
# with a different command override.

variable "archive_task_enabled" {
  description = "Enable the archive email scheduled task"
  type        = bool
  default     = true
}

variable "archive_container_image" {
  description = "Docker image for the archive task (same as API)"
  type        = string
  default     = "ghcr.io/trigpointinguk/platform/api:develop"
}

variable "archive_schedule_expression" {
  description = "EventBridge schedule expression for archive task"
  type        = string
  default     = "cron(0 3 * * ? *)"
}

# RDS credentials for the archive job (same JSON keys as the FastAPI ECS service:
# host, port, username, password, dbname — see modules/ecs-service).
variable "archive_postgres_credentials_secret_name" {
  description = "Secrets Manager secret name holding Postgres credentials for send_archives"
  type        = string
  default     = "fastapi-production-postgres-credentials"
}

data "aws_secretsmanager_secret" "archive_postgres_credentials" {
  count = var.archive_task_enabled ? 1 : 0
  name  = var.archive_postgres_credentials_secret_name
}

# Log group for archive task
resource "aws_cloudwatch_log_group" "archive" {
  count             = var.archive_task_enabled ? 1 : 0
  name              = "/aws/ecs/${var.project_name}-archive"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-archive-logs"
  }
}

# Task definition for the archive job
resource "aws_ecs_task_definition" "archive" {
  count                    = var.archive_task_enabled ? 1 : 0
  family                   = "${var.project_name}-archive"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name    = "${var.project_name}-archive"
      image   = var.archive_container_image
      command = ["python", "-m", "api.commands.send_archives"]
      environment = [
        { name = "ENVIRONMENT", value = "production" },
        # Explicit public API URL (archive task has no ALB; Pydantic FASTAPI_URL default is localhost).
        { name = "FASTAPI_URL", value = "https://api.trigpointing.uk" },
        { name = "LOG_LEVEL", value = "INFO" },
        { name = "DATABASE_POOL_SIZE", value = "2" },
        { name = "DATABASE_POOL_MAX_OVERFLOW", value = "3" },
        { name = "DATABASE_POOL_RECYCLE", value = "300" },
        { name = "DRY_RUN_ARCHIVES", value = "false" },
      ]
      # Without these, Settings defaults DB_HOST to localhost and the task exits before sending mail.
      secrets = [
        {
          name      = "DB_HOST"
          valueFrom = "${data.aws_secretsmanager_secret.archive_postgres_credentials[0].arn}:host::"
        },
        {
          name      = "DB_PORT"
          valueFrom = "${data.aws_secretsmanager_secret.archive_postgres_credentials[0].arn}:port::"
        },
        {
          name      = "DB_USER"
          valueFrom = "${data.aws_secretsmanager_secret.archive_postgres_credentials[0].arn}:username::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${data.aws_secretsmanager_secret.archive_postgres_credentials[0].arn}:password::"
        },
        {
          name      = "DB_NAME"
          valueFrom = "${data.aws_secretsmanager_secret.archive_postgres_credentials[0].arn}:dbname::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.archive[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "archive"
        }
      }
      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-archive-task"
  }
}

# IAM role for EventBridge to run the ECS task
resource "aws_iam_role" "archive_events" {
  count = var.archive_task_enabled ? 1 : 0
  name  = "${var.project_name}-archive-events-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-archive-events-role"
  }
}

resource "aws_iam_role_policy" "archive_events" {
  count = var.archive_task_enabled ? 1 : 0
  name  = "${var.project_name}-archive-events-policy"
  role  = aws_iam_role.archive_events[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = aws_ecs_task_definition.archive[0].arn
        Condition = {
          ArnLike = {
            "ecs:cluster" = aws_ecs_cluster.main.arn
          }
        }
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task_execution_role.arn,
          aws_iam_role.ecs_task_role.arn,
        ]
      }
    ]
  })
}

# EventBridge rule to trigger the task daily
resource "aws_cloudwatch_event_rule" "archive_schedule" {
  count               = var.archive_task_enabled ? 1 : 0
  name                = "${var.project_name}-archive-daily"
  description         = "Run archive email task daily at 03:00 UTC"
  schedule_expression = var.archive_schedule_expression

  tags = {
    Name = "${var.project_name}-archive-schedule"
  }
}

resource "aws_cloudwatch_event_target" "archive_ecs" {
  count    = var.archive_task_enabled ? 1 : 0
  rule     = aws_cloudwatch_event_rule.archive_schedule[0].name
  arn      = aws_ecs_cluster.main.arn
  role_arn = aws_iam_role.archive_events[0].arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.archive[0].arn
    task_count          = 1
    launch_type         = "FARGATE"

    network_configuration {
      subnets         = aws_subnet.private[*].id
      security_groups = [] # Will inherit from task definition; add SG if needed
    }
  }
}
