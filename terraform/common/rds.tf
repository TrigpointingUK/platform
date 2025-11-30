# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "trigpointing-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "trigpointing-db-subnet-group"
  }
}

# RDS Parameter Group
resource "aws_db_parameter_group" "main" {
  family      = "mysql8.4"
  name_prefix = "trigpointing-db-params-"

  parameter {
    name         = "innodb_buffer_pool_size"
    value        = "{DBInstanceClassMemory*3/4}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "slow_query_log"
    value        = "1"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_queries_not_using_indexes"
    value        = "1"
    apply_method = "immediate"
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      parameter,
      tags
    ]
  }

  tags = {
    Name = "trigpointing-db-params"
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "trigpointing-db"

  # Engine
  engine         = "mysql"
  engine_version = "8.4.6"
  instance_class = var.db_instance_class_mysql


  # Storage
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp2"
  storage_encrypted     = true

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Maintenance
  parameter_group_name        = aws_db_parameter_group.main.name
  backup_retention_period     = 7
  backup_window               = "03:00-04:00"
  maintenance_window          = "Sun:04:00-Sun:05:00"
  auto_minor_version_upgrade  = false
  allow_major_version_upgrade = true

  # Monitoring (set to 0 to disable Enhanced Monitoring and reduce CloudWatch costs)
  # Valid values: 0, 1, 5, 10, 15, 30, 60 seconds
  # 0 = disabled, saves ~$0.50/instance/month
  # Basic CloudWatch metrics (CPU, connections, etc.) still available at 1-minute intervals
  monitoring_interval = 0
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn

  # Security
  deletion_protection       = false
  skip_final_snapshot       = true
  final_snapshot_identifier = "trigpointing-final-snapshot"

  # Initial admin user
  username = "admin"
  # Password is managed by AWS when manage_master_user_password is true

  # Password rotation
  manage_master_user_password = true

  # Performance Insights (configurable - set to false to disable, 7 days for free tier, 465+ for advanced)
  performance_insights_enabled = var.db_performance_insights_enabled
  # performance_insights_retention_period = var.db_performance_insights_retention_period

  tags = {
    Name = "trigpointing-db"
  }
}

# RDS Enhanced Monitoring Role
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "fastapi-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "fastapi-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
