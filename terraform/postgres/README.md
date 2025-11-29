# PostgreSQL Terraform Configuration

⚠️ **IMPORTANT: This Terraform configuration can ONLY be run from the bastion host!**

## Why Bastion Host Required

This directory contains PostgreSQL Terraform configuration that:
- Creates PostgreSQL databases and users
- Requires direct connection to RDS instance
- RDS is in private subnet, only accessible from bastion host
- Cannot be run locally due to network restrictions

## Usage

### Option 1: Integrated Deployment (Recommended)
```bash
# From your local machine in terraform/ directory
./deploy.sh postgres
```

This will:
1. Copy all PostgreSQL files to bastion host (bastion.trigpointing.uk)
2. Run terraform on bastion
3. Deploy PostgreSQL databases and users

### Option 2: Manual SSH Deployment
```bash
# SSH to bastion
ssh -i ~/.ssh/trigpointing-bastion.pem ec2-user@bastion.trigpointing.uk

# Navigate to terraform directory
cd /home/ec2-user/postgres-terraform

# Run terraform commands
terraform init -backend-config=backend.conf
terraform plan
terraform apply
```

## What This Creates

- **Databases**: `tuk_production`, `tuk_staging`
- **Users**: `fastapi_production`, `fastapi_staging`, `backups`
- **Extensions**: PostGIS enabled on all databases
- **Secrets**: Stored in AWS Secrets Manager for each user

## Connecting to Database

### RDS Master User (for administration)
```bash
# On bastion host
./connect-to-postgres-master.sh
```

### Application Users
Use the credentials stored in AWS Secrets Manager:
- `fastapi-production-postgres-credentials`
- `fastapi-staging-postgres-credentials`
- `trigpointing-postgres-backups-credentials`

## Safety Features

- Local `terraform` command is blocked (use main `./deploy.sh postgres` instead)
- Uses bastion.trigpointing.uk hostname (no hardcoded IPs)
- Clear error messages guide proper usage

## PostGIS Extensions

PostGIS is automatically enabled on all databases, providing:
- Spatial data types (GEOGRAPHY, GEOMETRY)
- Spatial indexing (GiST, SP-GiST)
- Spatial functions (ST_Distance, ST_DWithin, etc.)
- Support for SRID 4326 (WGS84) and 27700 (OSGB36)

## Troubleshooting

If you see "could not connect to server" errors:
1. Ensure you're running from bastion host
2. Check RDS security groups allow bastion access
3. Verify AWS credentials are configured on bastion
4. Use `./connect-to-postgres-master.sh` to test RDS connectivity
5. Verify bastion.trigpointing.uk resolves correctly

## Migration from MySQL

This PostgreSQL configuration is designed to work alongside the existing MySQL setup:
- **PostgreSQL**: For FastAPI backend (production & staging)
- **MySQL**: Continues to serve MediaWiki & phpBB (unchanged)

Both databases coexist on separate RDS instances in the same VPC.

