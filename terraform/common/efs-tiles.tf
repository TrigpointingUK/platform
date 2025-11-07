# EFS for OS tile caching

# Security group for Tiles EFS
resource "aws_security_group" "efs_tiles" {
  name        = "${var.project_name}-efs-tiles-sg"
  description = "Security group for OS Tiles EFS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from bastion for manual inspection"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-efs-tiles-sg"
  }
}

# Tiles EFS filesystem
resource "aws_efs_file_system" "tiles" {
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"
  encrypted        = true

  # Transition rarely-accessed tiles to Infrequent Access after 30 days
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name        = "tiles-efs"
    Application = "fastapi"
    Purpose     = "os-tile-cache"
  }
}

# Tiles EFS mount targets (one per AZ)
resource "aws_efs_mount_target" "tiles" {
  count           = length(aws_subnet.private)
  file_system_id  = aws_efs_file_system.tiles.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs_tiles.id]
}

# Tiles EFS access point with appropriate permissions for FastAPI
# Using root:root (uid=0, gid=0) as FastAPI container likely runs as root
# Adjust if your container uses a different user
resource "aws_efs_access_point" "tiles" {
  file_system_id = aws_efs_file_system.tiles.id

  posix_user {
    gid = 0
    uid = 0
  }

  root_directory {
    path = "/tiles"
    creation_info {
      owner_gid   = 0
      owner_uid   = 0
      permissions = "0755"
    }
  }

  tags = {
    Name        = "tiles-access-point"
    Application = "fastapi"
  }
}

