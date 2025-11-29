#!/bin/bash

# FastAPI Terraform Deployment Script
# This script helps deploy the consolidated infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if terraform is installed
check_terraform() {
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform first."
        exit 1
    fi
    print_success "Terraform is installed: $(terraform version -json | jq -r '.terraform_version')"
}

# Function to check if AWS CLI is configured
check_aws() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi

    print_success "AWS CLI is configured: $(aws sts get-caller-identity --query 'Account' --output text)"
}

# Function to deploy common infrastructure
deploy_common() {
    print_status "Deploying common infrastructure..."

    cd common

    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init -backend-config=backend.conf

    # Plan deployment
    print_status "Planning deployment..."
    terraform plan

    # Ask for confirmation
    read -p "Do you want to apply the common infrastructure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply -auto-approve
        print_success "Common infrastructure deployed successfully!"

        # Note: Using existing tuk-terraform-state bucket in eu-west-1
        print_status "Using existing tuk-terraform-state bucket in eu-west-1"
    else
        print_warning "Common infrastructure deployment cancelled."
        exit 1
    fi

    cd ..
}

# Function to deploy staging
deploy_staging() {
    print_status "Deploying staging environment..."

    cd staging

    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init -backend-config=backend.conf

    # Plan deployment
    print_status "Planning deployment..."
    terraform plan

    # Ask for confirmation
    read -p "Do you want to apply the staging infrastructure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply -auto-approve
        print_success "Staging infrastructure deployed successfully!"

        # Show outputs
        print_status "Staging outputs:"
        terraform output
    else
        print_warning "Staging infrastructure deployment cancelled."
    fi

    cd ..
}

# Function to deploy production
deploy_production() {
    print_status "Deploying production environment..."

    cd production

    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init -backend-config=backend.conf

    # Plan deployment
    print_status "Planning deployment..."
    terraform plan

    # Ask for confirmation
    read -p "Do you want to apply the production infrastructure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply -auto-approve
        print_success "Production infrastructure deployed successfully!"

        # Show outputs
        print_status "Production outputs:"
        terraform output
    else
        print_warning "Production infrastructure deployment cancelled."
    fi

    cd ..
}


# Function to deploy MySQL databases
deploy_mysql() {
    print_status "Deploying MySQL databases..."

    # Configuration
    local bastion_host="bastion.trigpointing.uk"
    local ssh_key_path="${SSH_KEY_PATH:-~/.ssh/trigpointing-bastion.pem}"
    local bastion_user="ec2-user"
    local terraform_dir="/home/ec2-user/mysql-terraform"

    # Expand tilde in SSH key path
    local ssh_key_path_expanded="${ssh_key_path/#\~/$HOME}"

    # Check if SSH key exists
    if [[ ! -f "${ssh_key_path_expanded}" ]]; then
        print_error "SSH key not found at ${ssh_key_path_expanded}"
        print_error "Please set SSH_KEY_PATH environment variable or ensure ~/.ssh/trigpointing-bastion.pem exists"
        exit 1
    fi

    # Check if we can connect to bastion
    print_status "Testing connection to bastion host..."
    if ! ssh -i "${ssh_key_path_expanded}" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${bastion_user}@${bastion_host}" "echo 'Connection successful'" > /dev/null 2>&1; then
        print_error "Cannot connect to bastion host at ${bastion_host}"
        print_error "Please check:"
        print_error "  - Bastion hostname resolves correctly"
        print_error "  - SSH key path is correct: ${ssh_key_path_expanded}"
        print_error "  - SSH key has access to bastion"
        exit 1
    fi

    print_status "Copying MySQL Terraform files to bastion host..."

    # Create directory on bastion
    ssh -i "${ssh_key_path_expanded}" "${bastion_user}@${bastion_host}" "mkdir -p ${terraform_dir}"

    # Copy MySQL Terraform files from mysql directory
    if [ ! -d "mysql" ]; then
        print_error "MySQL terraform directory not found. Please run this from the terraform directory."
        exit 1
    fi

    cd mysql
    print_status "Excluding .terraform directory to avoid copying providers..."

    # Try rsync first (faster and more efficient)
    if command -v rsync > /dev/null 2>&1; then
        rsync -avz --exclude='.terraform/' --exclude='.terraform.lock.hcl' -e "ssh -i ${ssh_key_path_expanded}" ./ "${bastion_user}@${bastion_host}:${terraform_dir}/"
    else
        # Fallback to scp with tar for exclusions
        print_status "Using tar+scp fallback (rsync not available)..."
        tar --exclude='.terraform' --exclude='.terraform.lock.hcl' -czf - . | ssh -i "${ssh_key_path_expanded}" "${bastion_user}@${bastion_host}" "cd ${terraform_dir} && tar -xzf -"
    fi

    print_status "Running terraform on bastion host..."

    # Execute the deployment on bastion
    ssh -i "${ssh_key_path_expanded}" "${bastion_user}@${bastion_host}" "cd ${terraform_dir} && chmod +x deploy_mysql_on_bastion.sh && ./deploy_mysql_on_bastion.sh"

    cd ..

    print_success "MySQL deployment completed successfully!"
}

# Function to deploy PostgreSQL databases
deploy_postgres() {
    print_status "Deploying PostgreSQL databases..."

    # Configuration
    local bastion_host="bastion.trigpointing.uk"
    local ssh_key_path="${SSH_KEY_PATH:-~/.ssh/trigpointing-bastion.pem}"
    local bastion_user="ec2-user"
    local terraform_dir="/home/ec2-user/postgres-terraform"

    # Expand tilde in SSH key path
    local ssh_key_path_expanded="${ssh_key_path/#\~/$HOME}"

    # Check if SSH key exists
    if [[ ! -f "${ssh_key_path_expanded}" ]]; then
        print_error "SSH key not found at ${ssh_key_path_expanded}"
        print_error "Please set SSH_KEY_PATH environment variable or ensure ~/.ssh/trigpointing-bastion.pem exists"
        exit 1
    fi

    # Check if we can connect to bastion
    print_status "Testing connection to bastion host..."
    if ! ssh -i "${ssh_key_path_expanded}" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "${bastion_user}@${bastion_host}" "echo 'Connection successful'" > /dev/null 2>&1; then
        print_error "Cannot connect to bastion host at ${bastion_host}"
        print_error "Please check:"
        print_error "  - Bastion hostname resolves correctly"
        print_error "  - SSH key path is correct: ${ssh_key_path_expanded}"
        print_error "  - SSH key has access to bastion"
        exit 1
    fi

    print_status "Copying PostgreSQL Terraform files to bastion host..."

    # Create directory on bastion
    ssh -i "${ssh_key_path_expanded}" "${bastion_user}@${bastion_host}" "mkdir -p ${terraform_dir}"

    # Copy PostgreSQL Terraform files from postgres directory
    if [ ! -d "postgres" ]; then
        print_error "PostgreSQL terraform directory not found. Please run this from the terraform directory."
        exit 1
    fi

    cd postgres
    print_status "Excluding .terraform directory to avoid copying providers..."

    # Try rsync first (faster and more efficient)
    if command -v rsync > /dev/null 2>&1; then
        rsync -avz --exclude='.terraform/' --exclude='.terraform.lock.hcl' -e "ssh -i ${ssh_key_path_expanded}" ./ "${bastion_user}@${bastion_host}:${terraform_dir}/"
    else
        # Fallback to scp with tar for exclusions
        print_status "Using tar+scp fallback (rsync not available)..."
        tar --exclude='.terraform' --exclude='.terraform.lock.hcl' -czf - . | ssh -i "${ssh_key_path_expanded}" "${bastion_user}@${bastion_host}" "cd ${terraform_dir} && tar -xzf -"
    fi

    print_status "Running terraform on bastion host..."

    # Execute the deployment on bastion
    ssh -i "${ssh_key_path_expanded}" "${bastion_user}@${bastion_host}" "cd ${terraform_dir} && chmod +x deploy_postgres_on_bastion.sh && ./deploy_postgres_on_bastion.sh"

    cd ..

    print_success "PostgreSQL deployment completed successfully!"
}

# Function to show status
show_status() {
    print_status "Infrastructure Status:"
    echo

    # Check common infrastructure
    if [ -d "common" ] && [ -f "common/terraform.tfstate" ]; then
        print_success "Common infrastructure: Deployed"
        cd common
        echo "  State bucket: tuk-terraform-state (eu-west-1)"
        echo "  VPC ID: $(terraform output -raw vpc_id 2>/dev/null || echo 'Not available')"
        echo "  Bastion IP: $(terraform output -raw bastion_public_ip 2>/dev/null || echo 'Not available')"
        cd ..
    else
        print_warning "Common infrastructure: Not deployed"
    fi

    # Check staging
    if [ -d "staging" ] && [ -f "staging/terraform.tfstate" ]; then
        print_success "Staging environment: Deployed"
        cd staging
        echo "  ALB DNS: $(terraform output -raw alb_dns_name 2>/dev/null || echo 'Not available')"
        cd ..
    else
        print_warning "Staging environment: Not deployed"
    fi

    # Check production
    if [ -d "production" ] && [ -f "production/terraform.tfstate" ]; then
        print_success "Production environment: Deployed"
        cd production
        echo "  ALB DNS: $(terraform output -raw alb_dns_name 2>/dev/null || echo 'Not available')"
        cd ..
    else
        print_warning "Production environment: Not deployed"
    fi

    # Check MySQL
    if [ -d "mysql" ] && [ -f "mysql/terraform.tfstate" ]; then
        print_success "MySQL databases: Deployed"
        cd mysql
        echo "  Production schema: $(terraform output -raw production_schema_name 2>/dev/null || echo 'Not available')"
        echo "  Staging schema: $(terraform output -raw staging_schema_name 2>/dev/null || echo 'Not available')"
        cd ..
    else
        print_warning "MySQL databases: Not deployed"
    fi
}

# Main script
main() {
    echo "FastAPI Terraform Deployment Script"
    echo "==================================="
    echo

    # Check prerequisites
    check_terraform
    check_aws
    echo

    # Parse command line arguments
    case "${1:-}" in
        "common")
            deploy_common
            ;;
        "staging")
            deploy_staging
            ;;
        "production")
            deploy_production
            ;;
        "monitoring")
            deploy_monitoring
            ;;
        "mysql")
            deploy_mysql
            ;;
        "postgres")
            deploy_postgres
            ;;
        "all")
            deploy_common
            echo
            deploy_staging
            echo
            deploy_production
            echo
            deploy_monitoring
            echo
            deploy_mysql
            echo
            deploy_postgres
            ;;
        "status")
            show_status
            ;;
        *)
            echo "Usage: $0 {common|staging|production|monitoring|mysql|postgres|all|status}"
            echo
            echo "Commands:"
            echo "  common     - Deploy common infrastructure (VPC, ECS, RDS, etc.)"
            echo "  staging    - Deploy staging environment"
            echo "  production - Deploy production environment"
            echo "  monitoring - Deploy monitoring stack (Synthetics, SNS, Slack)"
            echo "  mysql      - Deploy MySQL databases (runs on bastion host)"
            echo "  postgres   - Deploy PostgreSQL databases and schemas (runs on bastion host)"
            echo "  all        - Deploy all infrastructure in order"
            echo "  status     - Show current deployment status"
            echo
            echo "Deployment order:"
            echo "  1. common (first time only)"
            echo "  2. staging"
            echo "  3. production"
            echo "  4. monitoring"
            echo "  5. mysql"
            echo
            echo "Note: MySQL deployment requires SSH access to bastion.trigpointing.uk"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
