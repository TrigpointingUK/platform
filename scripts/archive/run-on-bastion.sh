#!/bin/bash
# Copy and run database export script on bastion host

set -e

BASTION_HOST="bastion.trigpointing.uk"
KEY_PATH="~/.ssh/your-key.pem"

echo "🚀 Copying script to bastion host..."

# Copy the Python script to bastion
scp -i $KEY_PATH scripts/export-database-schema.py ec2-user@$BASTION_HOST:~/

# Copy requirements for the script
echo -e "pymysql\nsqlalchemy\npyyaml" > /tmp/schema_requirements.txt
scp -i $KEY_PATH /tmp/schema_requirements.txt ec2-user@$BASTION_HOST:~/

echo "📦 Running script on bastion host..."

# Run the script on bastion
ssh -i $KEY_PATH ec2-user@$BASTION_HOST << 'EOF'
# Install Python dependencies
pip3 install --user -r schema_requirements.txt

# Set environment variables
export DB_HOST=fastapi-staging-db.cykrokraghk3.us-west-2.rds.amazonaws.com
export DB_USER=fastapi_user
export DB_PASSWORD=change-this-password-in-production
export DB_NAME=trigpoin_trigs

# Run the schema export
python3 export-database-schema.py

# Show what was created
ls -la docs/database/
EOF

echo "📥 Copying results back..."

# Copy the results back
scp -i $KEY_PATH -r ec2-user@$BASTION_HOST:~/docs/database ./docs/

echo "✅ Schema export complete! Check ./docs/database/"
