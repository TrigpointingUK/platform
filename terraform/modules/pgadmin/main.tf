# CloudWatch Log Group for pgAdmin
resource "aws_cloudwatch_log_group" "pgadmin" {
  name              = "/aws/ecs/${var.project_name}-pgadmin-${var.environment}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-pgadmin-${var.environment}-logs"
  }
}

# ECS Task Definition for pgAdmin
resource "aws_ecs_task_definition" "pgadmin" {
  family                   = "${var.project_name}-pgadmin-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-pgadmin"
      image = "dpage/pgadmin4:latest"
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "PGADMIN_DEFAULT_EMAIL"
          value = var.pgadmin_email
        },
        {
          name  = "PGADMIN_DEFAULT_PASSWORD"
          value = var.pgadmin_password
        },
        {
          name  = "PGADMIN_CONFIG_SERVER_MODE"
          value = "True"
        },
        {
          name  = "PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED"
          value = "False"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.pgadmin.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }
      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-pgadmin-${var.environment}-task-definition"
  }
}

# ECS Service for pgAdmin
resource "aws_ecs_service" "pgadmin" {
  name            = "${var.project_name}-pgadmin-${var.environment}"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.pgadmin.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "${var.project_name}-pgadmin"
    container_port   = 80
  }

  tags = {
    Name = "${var.project_name}-pgadmin-${var.environment}-service"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "pgadmin" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.pgadmin.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "pgadmin_cpu" {
  name               = "${var.project_name}-pgadmin-${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.pgadmin.resource_id
  scalable_dimension = aws_appautoscaling_target.pgadmin.scalable_dimension
  service_namespace  = aws_appautoscaling_target.pgadmin.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_value
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

