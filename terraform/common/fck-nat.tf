# fck-nat instances to replace expensive NAT gateways
# fck-nat is a cost-effective alternative to AWS NAT gateways

# Security group for fck-nat instances
resource "aws_security_group" "fck_nat" {
  name_prefix = "${var.project_name}-fck-nat-"
  vpc_id      = aws_vpc.main.id

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow inbound traffic from private subnets
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Allow SSH access for management (optional)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-fck-nat-sg"
  }
}

# Data source for the latest fck-nat AMI
data "aws_ami" "fck_nat" {
  most_recent = true
  owners      = ["568608671756"] # fck-nat AMI owner

  filter {
    name   = "name"
    values = ["fck-nat-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

# fck-nat instance (single instance in first AZ)
resource "aws_instance" "fck_nat" {
  count = 1

  ami                    = data.aws_ami.fck_nat.id
  instance_type          = "t4g.nano" # Graviton arm64, same price as t3.nano
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.fck_nat.id]
  source_dest_check      = false # Required for NAT functionality

  # Enable detailed monitoring for better observability
  monitoring = true

  tags = {
    Name = "${var.project_name}-fck-nat"
    Type = "fck-nat"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for fck-nat instance
resource "aws_eip" "fck_nat" {
  count = 1

  instance = aws_instance.fck_nat[0].id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-fck-nat-eip"
  }

  depends_on = [aws_internet_gateway.main]
}

# Use null_resource to replace existing NAT gateway routes with fck-nat routes
# This runs once per route table, but all point to the single fck-nat instance
resource "null_resource" "replace_nat_routes" {
  count = length(var.availability_zones)

  depends_on = [aws_instance.fck_nat]

  provisioner "local-exec" {
    command = <<-EOT
      set -e

      # Set AWS region
      export AWS_DEFAULT_REGION=${var.aws_region}

      echo "Getting network interface ID for fck-nat instance ${aws_instance.fck_nat[0].id}"

      # Get the network interface ID of the fck-nat instance
      NETWORK_INTERFACE_ID=$(aws ec2 describe-instances \
        --region ${var.aws_region} \
        --instance-ids ${aws_instance.fck_nat[0].id} \
        --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
        --output text)

      if [ -z "$NETWORK_INTERFACE_ID" ] || [ "$NETWORK_INTERFACE_ID" = "None" ]; then
        echo "Error: Could not get network interface ID for instance ${aws_instance.fck_nat[0].id}"
        exit 1
      fi

      echo "Configuring route in route table ${aws_route_table.private[count.index].id} to use fck-nat instance network interface $NETWORK_INTERFACE_ID"

      # Try to replace the existing route, or create it if it doesn't exist
      if ! aws ec2 replace-route \
        --region ${var.aws_region} \
        --route-table-id ${aws_route_table.private[count.index].id} \
        --destination-cidr-block 0.0.0.0/0 \
        --network-interface-id $NETWORK_INTERFACE_ID 2>/dev/null; then
        
        echo "Route doesn't exist, creating new route..."
        aws ec2 create-route \
          --region ${var.aws_region} \
          --route-table-id ${aws_route_table.private[count.index].id} \
          --destination-cidr-block 0.0.0.0/0 \
          --network-interface-id $NETWORK_INTERFACE_ID
      fi

      echo "Successfully configured route for route table ${aws_route_table.private[count.index].id}"
    EOT
  }

  triggers = {
    fck_nat_instance_id = aws_instance.fck_nat[0].id
    route_table_id      = aws_route_table.private[count.index].id
  }
}
