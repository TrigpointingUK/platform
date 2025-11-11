# CloudWatch Log Group for SPA
resource "aws_cloudwatch_log_group" "spa" {
  name              = "/aws/ecs/${var.project_name}-spa-${var.environment}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-spa-${var.environment}-logs"
  }
}

# ECS Task Definition for SPA (nginx serving static React build)
resource "aws_ecs_task_definition" "spa" {
  family                   = "${var.project_name}-spa-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "${var.project_name}-spa"
      image = var.image_uri
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.spa.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-spa-${var.environment}-task-definition"
  }
}

# Target Group for SPA
resource "aws_lb_target_group" "spa" {
  name        = "${var.project_name}-spa-${var.environment}-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-spa-${var.environment}-tg"
  }
}

# ALB Listener Rule for SPA (host-based routing, optionally with path patterns)
# Can be disabled if you want to create a custom rule with OIDC authentication
resource "aws_lb_listener_rule" "spa" {
  count        = var.create_listener_rule ? 1 : 0
  listener_arn = var.alb_listener_arn
  priority     = var.alb_rule_priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.spa.arn
  }

  condition {
    host_header {
      values = var.host_headers
    }
  }

  # Only add path_pattern condition if path_patterns is not null
  dynamic "condition" {
    for_each = var.path_patterns != null ? [1] : []
    content {
      path_pattern {
        values = var.path_patterns
      }
    }
  }

  tags = {
    Name = "${var.project_name}-spa-${var.environment}-listener-rule"
  }
}

# ECS Service for SPA
resource "aws_ecs_service" "spa" {
  name                   = "${var.project_name}-spa-${var.environment}"
  cluster                = var.ecs_cluster_id
  task_definition        = aws_ecs_task_definition.spa.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.spa.arn
    container_name   = "${var.project_name}-spa"
    container_port   = 80
  }

  tags = {
    Name = "${var.project_name}-spa-${var.environment}-service"
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "spa" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.spa.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "spa_cpu" {
  name               = "${var.project_name}-spa-${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.spa.resource_id
  scalable_dimension = aws_appautoscaling_target.spa.scalable_dimension
  service_namespace  = aws_appautoscaling_target.spa.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.cpu_target_value
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

