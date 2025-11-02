# EFS for phpBB persistent storage

# Security group for Valkey EFS
resource "aws_security_group" "efs_valkey" {
  name        = "${var.project_name}-efs-valkey-sg"
  description = "Security group for Valkey EFS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from Valkey ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.valkey_ecs.id]
  }

  ingress {
    description     = "NFS from bastion"
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
    Name = "${var.project_name}-efs-valkey-sg"
  }
}

# Security group for phpBB EFS
resource "aws_security_group" "efs_phpbb" {
  name        = "${var.project_name}-efs-phpbb-sg"
  description = "Security group for phpBB EFS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from phpBB ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.phpbb_ecs.id]
  }

  ingress {
    description     = "NFS from bastion"
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
    Name = "${var.project_name}-efs-phpbb-sg"
  }
}

# Security group for MediaWiki EFS
resource "aws_security_group" "efs_mediawiki" {
  name        = "${var.project_name}-efs-mediawiki-sg"
  description = "Security group for MediaWiki EFS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from MediaWiki ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.mediawiki_ecs.id]
  }

  ingress {
    description     = "NFS from bastion"
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
    Name = "${var.project_name}-efs-mediawiki-sg"
  }
}

# phpBB EFS filesystem
resource "aws_efs_file_system" "phpbb" {
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  encrypted = true

  tags = {
    Name        = "phpbb-efs"
    Application = "phpbb"
  }
}

# phpBB EFS mount targets
resource "aws_efs_mount_target" "phpbb" {
  count           = length(aws_subnet.private)
  file_system_id  = aws_efs_file_system.phpbb.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs_phpbb.id]
}

# phpBB EFS access point with www-data uid/gid=33 so Fargate writes as phpBB
resource "aws_efs_access_point" "phpbb" {
  file_system_id = aws_efs_file_system.phpbb.id

  posix_user {
    gid = 33
    uid = 33
  }

  root_directory {
    path = "/phpbb"
    creation_info {
      owner_gid   = 33
      owner_uid   = 33
      permissions = "0775"
    }
  }

  tags = {
    Name        = "phpbb-access-point"
    Application = "phpbb"
  }
}

# MediaWiki EFS filesystem
resource "aws_efs_file_system" "mediawiki" {
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"
  encrypted        = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name        = "mediawiki-efs"
    Application = "mediawiki"
  }
}

# MediaWiki EFS mount targets
resource "aws_efs_mount_target" "mediawiki" {
  count           = length(aws_subnet.private)
  file_system_id  = aws_efs_file_system.mediawiki.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs_mediawiki.id]
}

# MediaWiki EFS access point with www-data uid/gid=33 so Fargate writes as www-data
resource "aws_efs_access_point" "mediawiki" {
  file_system_id = aws_efs_file_system.mediawiki.id

  posix_user {
    gid = 33
    uid = 33
  }

  root_directory {
    path = "/mediawiki"
    creation_info {
      owner_gid   = 33
      owner_uid   = 33
      permissions = "0775"
    }
  }

  tags = {
    Name        = "mediawiki-access-point"
    Application = "mediawiki"
  }
}
