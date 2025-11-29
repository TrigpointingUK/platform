# Security Groups
resource "aws_security_group" "rds" {
  name        = "fastapi-rds-sg"
  description = "Security group for RDS database"
  vpc_id      = aws_vpc.main.id

  # MySQL access from ECS tasks (will be added by environment-specific configs)
  ingress {
    description = "MySQL from ECS tasks"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # MySQL access from bastion host
  ingress {
    description     = "MySQL from bastion host"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  # MySQL access from phpMyAdmin ECS tasks
  ingress {
    description     = "MySQL from phpMyAdmin ECS tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.phpmyadmin_ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "fastapi-rds-sg"
  }

  # Ignore changes to ingress rules managed separately
  lifecycle {
    ignore_changes = [ingress]
  }
}

# ## SSM interface endpoints removed (cost); ECS Exec will use NAT egress
# ## Re-introduce Interface Endpoints for ECS Exec reliability

# resource "aws_security_group" "vpc_endpoints" {
#   name        = "${var.project_name}-vpc-endpoints-sg"
#   description = "SG for VPC Interface Endpoints (SSM/EC2Messages/SSMMessages)"
#   vpc_id      = aws_vpc.main.id

#   # Allow HTTPS from ECS tasks SG
#   ingress {
#     from_port       = 443
#     to_port         = 443
#     protocol        = "tcp"
#     security_groups = [aws_security_group.phpbb_ecs.id]
#     description     = "HTTPS from phpBB ECS tasks"
#   }

#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

# Security group for Valkey ECS service
resource "aws_security_group" "valkey_ecs" {
  name        = "${var.project_name}-valkey-ecs-sg"
  description = "Security group for Valkey ECS service"
  vpc_id      = aws_vpc.main.id

  # All ingress rules managed via aws_security_group_rule resources below
  # to allow environment-specific rules to be added without conflicts

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-valkey-ecs-sg"
  }

  lifecycle {
    # Ignore changes to ingress rules as they're managed separately
    ignore_changes = [ingress]
  }
}

# Valkey ingress rules - managed separately to allow environment-specific additions
resource "aws_security_group_rule" "valkey_from_mediawiki" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.mediawiki_ecs.id
  security_group_id        = aws_security_group.valkey_ecs.id
  description              = "Valkey from MediaWiki ECS tasks"
}

resource "aws_security_group_rule" "valkey_from_phpbb" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.phpbb_ecs.id
  security_group_id        = aws_security_group.valkey_ecs.id
  description              = "Valkey from phpBB ECS tasks"
}

resource "aws_security_group_rule" "valkey_from_bastion" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.valkey_ecs.id
  description              = "Valkey from bastion (for maintenance)"
}

resource "aws_security_group_rule" "redis_commander_from_alb" {
  type                     = "ingress"
  from_port                = 8081
  to_port                  = 8081
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.valkey_ecs.id
  description              = "Redis Commander from ALB"
}

# Security group for nginx proxy ECS service - DECOMMISSIONED
# resource "aws_security_group" "nginx_proxy_ecs" {
#   name        = "${var.project_name}-nginx-proxy-ecs-sg"
#   description = "Security group for nginx reverse proxy ECS service"
#   vpc_id      = aws_vpc.main.id
#
#   ingress {
#     description     = "HTTP from ALB"
#     from_port       = 80
#     to_port         = 80
#     protocol        = "tcp"
#     security_groups = [aws_security_group.alb.id]
#   }
#
#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#     description = "Allow all outbound traffic (needed to reach legacy server)"
#   }
#
#   tags = {
#     Name = "${var.project_name}-nginx-proxy-ecs-sg"
#   }
# }

