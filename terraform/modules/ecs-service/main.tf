# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  # Optional EFS volume for tile caching
  dynamic "volume" {
    for_each = var.efs_file_system_id != null ? [1] : []
    content {
      name = "tiles-efs"
      efs_volume_configuration {
        file_system_id     = var.efs_file_system_id
        transit_encryption = "ENABLED"
        authorization_config {
          access_point_id = var.efs_access_point_id
          iam             = "ENABLED"
        }
      }
    }
  }

  container_definitions = jsonencode(concat([
    {
      name  = "${var.project_name}-app"
      image = var.container_image
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      environment = concat([
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "JWT_ALGORITHM"
          value = "HS256"
        },
        {
          name  = "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
          value = "30"
        },
        {
          name  = "DEBUG"
          value = var.environment == "production" ? "false" : "true"
        },
        {
          name  = "UVICORN_HOST"
          value = "0.0.0.0"
        },
        {
          name  = "LOG_LEVEL"
          value = var.log_level
        },
        {
          name  = "DATABASE_POOL_SIZE"
          value = tostring(var.db_pool_size)
        },
        {
          name  = "DATABASE_POOL_RECYCLE"
          value = tostring(var.db_pool_recycle)
        },
        {
          name  = "PROFILING_ENABLED"
          value = tostring(var.profiling_enabled)
        },
        {
          name  = "PROFILING_DEFAULT_FORMAT"
          value = var.profiling_default_format
        },
        {
          name  = "PHOTOS_S3_BUCKET"
          value = var.photos_s3_bucket
        },
        {
          name  = "PHOTOS_SERVER_ID"
          value = tostring(var.photos_server_id)
        }
        ],
        # Optional base environment variables
        var.cors_origins != null ? [
          {
            name  = "BACKEND_CORS_ORIGINS"
            value = jsonencode(var.cors_origins)
          }
        ] : [],
        var.redis_url != "" ? [
          {
            name  = "REDIS_URL"
            value = var.redis_url
          }
        ] : [],
      )

      # Secrets from AWS Secrets Manager
      secrets = concat([
        # Database Credentials
        {
          name      = "DB_HOST"
          valueFrom = "${var.credentials_secret_arn}:host::"
        },
        {
          name      = "DB_PORT"
          valueFrom = "${var.credentials_secret_arn}:port::"
        },
        {
          name      = "DB_USER"
          valueFrom = "${var.credentials_secret_arn}:username::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${var.credentials_secret_arn}:password::"
        },
        {
          name      = "DB_NAME"
          valueFrom = "${var.credentials_secret_arn}:dbname::"
        }
        ],
        # Auth0 secrets (required)
        [
          {
            name      = "AUTH0_API_AUDIENCE"
            valueFrom = "${var.secrets_arn}:auth0_api_audience::"
          },
          {
            name      = "AUTH0_CONNECTION"
            valueFrom = "${var.secrets_arn}:auth0_connection::"
          },
          {
            name      = "AUTH0_CUSTOM_DOMAIN"
            valueFrom = "${var.secrets_arn}:auth0_custom_domain::"
          },
          {
            name      = "AUTH0_TENANT_DOMAIN"
            valueFrom = "${var.secrets_arn}:auth0_tenant_domain::"
          },
          {
            name      = "AUTH0_M2M_CLIENT_ID"
            valueFrom = "${var.secrets_arn}:auth0_m2m_client_id::"
          },
          {
            name      = "AUTH0_M2M_CLIENT_SECRET"
            valueFrom = "${var.secrets_arn}:auth0_m2m_client_secret::"
          },
          {
            name      = "AUTH0_SPA_CLIENT_ID"
            valueFrom = "${var.secrets_arn}:auth0_spa_client_id::"
          },
          {
            name      = "WEBHOOK_SHARED_SECRET"
            valueFrom = "${var.secrets_arn}:webhook_shared_secret::"
          }
        ],
        # tile caching
        [
          {
            name      = "OS_API_KEY"
            valueFrom = "${var.secrets_arn}:os_api_key::"
          }
        ]
      )
      mountPoints = var.efs_file_system_id != null ? [
        {
          sourceVolume  = "tiles-efs"
          containerPath = "/mnt/tiles"
          readOnly      = false
        }
      ] : []
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.cloudwatch_log_group_name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=10)\" || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
      essential = true
    }
  ]))

  tags = {
    Name = "${var.project_name}-${var.environment}-task-definition"
  }
}

# IAM policy for ECS tasks to read database credentials and secrets
resource "aws_iam_policy" "ecs_credentials_access" {
  name        = "${var.project_name}-${var.environment}-ecs-credentials-access"
  description = "Allow ECS tasks to read database credentials and application secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          var.secrets_arn,
          var.credentials_secret_arn
        ]
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-credentials-access"
  }
}

# ECS Service
resource "aws_ecs_service" "app" {
  name                   = var.service_name != null ? var.service_name : "${var.project_name}-${var.environment}"
  cluster                = var.ecs_cluster_id
  task_definition        = aws_ecs_task_definition.app.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "${var.project_name}-app"
    container_port   = 8000
  }

  # Listener rules are managed by the target-group module (host-based routing)

  tags = {
    Name = "${var.project_name}-${var.environment}-service"
  }
}

# Removed path-based listener rule; host-based rules are managed by target-group module

# Auto Scaling Target
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = {
    Name = "${var.project_name}-${var.environment}-autoscaling-target"
  }
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "ecs_policy_cpu" {
  name               = "${var.project_name}-${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_value
    scale_in_cooldown  = 300 # 5 minutes
    scale_out_cooldown = 60  # 1 minute
  }
}

# Auto Scaling Policy - Memory (commented out to reduce CloudWatch costs)
# resource "aws_appautoscaling_policy" "ecs_policy_memory" {
#   name               = "${var.project_name}-${var.environment}-memory-scaling"
#   policy_type        = "TargetTrackingScaling"
#   resource_id        = aws_appautoscaling_target.ecs_target.resource_id
#   scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
#   service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace
#
#   target_tracking_scaling_policy_configuration {
#     predefined_metric_specification {
#       predefined_metric_type = "ECSServiceAverageMemoryUtilization"
#     }
#     target_value = var.memory_target_value
#   }
# }

# Attach credentials access policy to ECS task role
resource "aws_iam_role_policy_attachment" "ecs_task_credentials" {
  role       = var.ecs_task_role_name
  policy_arn = aws_iam_policy.ecs_credentials_access.arn
}

# Attach credentials access policy to ECS task execution role
resource "aws_iam_role_policy_attachment" "ecs_task_execution_credentials" {
  role       = var.ecs_task_execution_role_name
  policy_arn = aws_iam_policy.ecs_credentials_access.arn
}
