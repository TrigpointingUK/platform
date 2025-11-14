#!/bin/bash
# Deployment script for PostgreSQL Terraform configuration
# This script is run from the bastion host

set -e

# Script variables
TERRAFORM_DIR="/home/ec2-user/postgres-terraform"
BACKEND_CONF="backend.conf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}PostgreSQL Terraform Deployment${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Navigate to terraform directory
cd "$TERRAFORM_DIR"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo -e "${YELLOW}Initializing Terraform...${NC}"
    terraform init -backend-config="$BACKEND_CONF"
else
    echo -e "${GREEN}Terraform already initialized${NC}"
fi

# Run terraform plan
echo ""
echo -e "${YELLOW}Running terraform plan...${NC}"
terraform plan -out=tfplan

# Ask for confirmation
echo ""
echo -e "${YELLOW}Do you want to apply these changes? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" = "yes" ]; then
    echo -e "${GREEN}Applying changes...${NC}"
    terraform apply tfplan
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo -e "${GREEN}======================================${NC}"
else
    echo -e "${RED}Deployment cancelled${NC}"
    rm -f tfplan
    exit 1
fi

# Clean up plan file
rm -f tfplan

echo ""
echo -e "${YELLOW}Note: Database credentials have been stored in AWS Secrets Manager${NC}"
echo -e "${YELLOW}Secret ARNs:${NC}"
terraform output | grep credentials_arn

