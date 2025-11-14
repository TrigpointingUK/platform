# PostgreSQL RDS Instance for FastAPI Backend
# MediaWiki and phpBB continue using MySQL

# PostgreSQL Subnet Group (reuse existing private subnets)
resource "aws_db_subnet_group" "postgres" {
  name       = "trigpointing-postgres-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "trigpointing-postgres-subnet-group"
  }
}

# PostgreSQL Parameter Group
resource "aws_db_parameter_group" "postgres" {
  family      = "postgres16"
  name_prefix = "trigpointing-postgres-params-"

  # PostGIS and performance tuning
  parameter {
    name         = "shared_buffers"
    value        = "{DBInstanceClassMemory/4096}" # 25% of instance memory
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "work_mem"
    value        = "16384" # 16MB for sorting/hashing operations
    apply_method = "immediate"
  }

  parameter {
    name         = "maintenance_work_mem"
    value        = "524288" # 512MB for index creation/VACUUM
    apply_method = "immediate"
  }

  parameter {
    name         = "effective_cache_size"
    value        = "{DBInstanceClassMemory*3/4096}" # 75% of instance memory
    apply_method = "immediate"
  }

  parameter {
    name         = "random_page_cost"
    value        = "1.1" # SSD optimization
    apply_method = "immediate"
  }

  # PostGIS-specific parameters
  parameter {
    name         = "max_locks_per_transaction"
    value        = "256" # Increased for spatial operations
    apply_method = "pending-reboot"
  }

  # Logging parameters
  parameter {
    name         = "log_min_duration_statement"
    value        = "1000" # Log queries > 1 second
    apply_method = "immediate"
  }

  parameter {
    name         = "log_connections"
    value        = "1"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_disconnections"
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
    Name = "trigpointing-postgres-params"
  }
}

# PostgreSQL RDS Instance
resource "aws_db_instance" "postgres" {
  identifier = "trigpointing-postgres"

  # Engine
  engine         = "postgres"
  engine_version = "16.6"
  instance_class = var.db_instance_class

  # Storage
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Network
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres_rds.id]
  publicly_accessible    = false

  # Maintenance
  parameter_group_name        = aws_db_parameter_group.postgres.name
  backup_retention_period     = 7
  backup_window               = "04:00-05:00"         # Different from MySQL (03:00-04:00)
  maintenance_window          = "Mon:05:00-Mon:06:00" # Different from MySQL (Sun)
  auto_minor_version_upgrade  = false
  allow_major_version_upgrade = true

  # Monitoring
  monitoring_interval = 0
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn

  # Security
  deletion_protection       = false
  skip_final_snapshot       = true
  final_snapshot_identifier = "trigpointing-postgres-final-snapshot"

  # Initial admin user
  username = "postgres"
  # Password is managed by AWS when manage_master_user_password is true

  # Password rotation
  manage_master_user_password = true

  # Performance Insights
  performance_insights_enabled = var.db_performance_insights_enabled

  tags = {
    Name = "trigpointing-postgres"
  }
}

# Security Group for PostgreSQL RDS
resource "aws_security_group" "postgres_rds" {
  name        = "${var.project_name}-postgres-rds"
  description = "Security group for PostgreSQL RDS instance"
  vpc_id      = aws_vpc.main.id

  # Allow PostgreSQL access from ECS tasks (FastAPI backend)
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.fastapi_ecs.id]
    description     = "PostgreSQL access from FastAPI ECS tasks"
  }

  # Allow PostgreSQL access from bastion host
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
    description     = "PostgreSQL access from bastion host"
  }

  # Allow PostgreSQL access from phpMyAdmin (for pgAdmin-like access)
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.phpmyadmin_ecs.id]
    description     = "PostgreSQL access from phpMyAdmin/pgAdmin"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-postgres-rds"
  }
}

