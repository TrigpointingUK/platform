# Valkey ECS Service Module
# Deploys Valkey with Redis Commander for management

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "valkey" {
  name              = "/aws/ecs/${var.project_name}-valkey"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-valkey-logs"
    Environment = var.environment
  }
}

# EFS File System for Valkey persistence
resource "aws_efs_file_system" "valkey" {
  creation_token = "${var.project_name}-valkey-data"
  encrypted      = true

  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name        = "${var.project_name}-valkey-efs"
    Environment = var.environment
    Purpose     = "Valkey RDB persistence"
  }
}

# EFS Mount Targets (one per private subnet)
resource "aws_efs_mount_target" "valkey" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.valkey.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [var.efs_security_group_id]
}

# EFS Access Point for Valkey
# Valkey Alpine runs as 'redis' user with uid=999, gid=999
resource "aws_efs_access_point" "valkey" {
  file_system_id = aws_efs_file_system.valkey.id

  root_directory {
    path = "/valkey-data"
    creation_info {
      owner_gid   = 999
      owner_uid   = 999
      permissions = "755"
    }
  }

  posix_user {
    gid = 999
    uid = 999
  }

  tags = {
    Name        = "${var.project_name}-valkey-access-point"
    Environment = var.environment
  }
}

# ECS Task Definition for Valkey + Redis Commander
resource "aws_ecs_task_definition" "valkey" {
  family                   = "${var.project_name}-valkey"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  # EFS volume for persistence
  volume {
    name = "valkey-data"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.valkey.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.valkey.id
        iam             = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name   = "valkey"
      image  = "valkey/valkey:7-alpine"
      user   = "999:999" # Run as valkey user to avoid chown issues with EFS
      cpu    = var.valkey_cpu
      memory = var.valkey_memory
      portMappings = [
        {
          containerPort = 6379
          protocol      = "tcp"
        }
      ]
      mountPoints = [
        {
          sourceVolume  = "valkey-data"
          containerPath = "/data"
          readOnly      = false
        }
      ]
      command = [
        "valkey-server",
        "--maxmemory", "${var.valkey_max_memory}",
        "--maxmemory-policy", "allkeys-lru",
        "--dir", "/data",                      # Store RDB files in EFS
        "--save", "900 1 300 10 60 10000",     # Save snapshots: 15min/1key, 5min/10keys, 1min/10000keys
        "--dbfilename", "dump.rdb",            # RDB filename
        "--rdbcompression", "yes",             # Compress RDB files
        "--stop-writes-on-bgsave-error", "no", # Don't stop writes on save errors
        "--oom-score-adj", "no",               # Disable OOM killer adjustments
        "--tcp-keepalive", "60",               # Keep connections alive
        "--timeout", "0"                       # Disable client timeout
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.valkey.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "valkey"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "valkey-cli ping || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
      essential = true
    },
    {
      name   = "redis-commander"
      image  = "ghcr.io/joeferner/redis-commander:latest"
      cpu    = var.commander_cpu
      memory = var.commander_memory
      portMappings = [
        {
          containerPort = 8081
          protocol      = "tcp"
        }
      ]
      command = [
        "node", "./bin/redis-commander",
        "--redis-host", "localhost",
        "--redis-port", "6379",
        "--no-http-auth"
      ]
      environment = [
        {
          name  = "REDIS_HOST"
          value = "localhost"
        },
        {
          name  = "REDIS_PORT"
          value = "6379"
        },
        {
          name  = "REDIS_COMMANDER_HOST"
          value = "0.0.0.0"
        },
        {
          name  = "REDIS_COMMANDER_PORT"
          value = "8081"
        }
      ]
      # Health check for Redis Commander - use netcat to check if port is open
      healthCheck = {
        command     = ["CMD-SHELL", "nc -z localhost 8081 || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.valkey.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "commander"
        }
      }
      essential = true
    }
  ])

  tags = {
    Name        = "${var.project_name}-valkey-task-definition"
    Environment = var.environment
  }
}

# ECS Service for Valkey
resource "aws_ecs_service" "valkey" {
  name                   = "${var.project_name}-valkey"
  cluster                = var.ecs_cluster_id
  task_definition        = aws_ecs_task_definition.valkey.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.valkey_security_group_id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = var.service_discovery_service_arn
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.valkey_commander.arn
    container_name   = "redis-commander"
    container_port   = 8081
  }

  tags = {
    Name        = "${var.project_name}-valkey-service"
    Environment = var.environment
  }

  depends_on = [var.service_discovery_service_arn]
}

# Target Group for Redis Commander
resource "aws_lb_target_group" "valkey_commander" {
  name        = "${var.project_name}-valkey-commander-tg"
  port        = 8081
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name        = "${var.project_name}-valkey-commander-tg"
    Environment = var.environment
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "valkey" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.valkey.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "valkey_cpu" {
  name               = "${var.project_name}-valkey-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.valkey.resource_id
  scalable_dimension = aws_appautoscaling_target.valkey.scalable_dimension
  service_namespace  = aws_appautoscaling_target.valkey.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_value
    scale_in_cooldown  = 300 # 5 minutes
    scale_out_cooldown = 60  # 1 minute
  }
}
