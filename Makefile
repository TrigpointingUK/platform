orientation-model:
	@echo "Creating orientation model with self-supervised rotations..."
	python -m pip install -q -r requirements-train.txt
	python scripts/train_export_orientation.py --data ./res/orientation_data --output ./res/models/orientation_classifier.onnx --epochs 3 --batch-size 64 --lr 1e-3
	@echo "Model exported to res/models/orientation_classifier.onnx"
.PHONY: help install install-dev test test-cov lint format type-check security build run clean docker-build docker-run docker-down mysql-client diff-cov \
	run-staging db-tunnel-staging-start db-tunnel-staging-stop mysql-staging \
	bastion-ssm-shell db-tunnel-staging-ssm-start postgres-tunnel-staging-ssm-start bastion-allow-my-ip bastion-revoke-my-ip \
	redis-tunnel-staging-ssm-start redis-cli-staging \
	test-db-start test-db-stop \
	web-install web-dev web-build web-test web-lint web-type-check \
	migration-create migration-upgrade migration-downgrade migration-history migration-current migration-check

# Default target
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Local development against STAGING via Bastion SSH tunnel (no Docker)
# ---------------------------------------------------------------------------

# Defaults (override on the command line or environment as needed)
AWS_REGION ?= eu-west-1
STAGING_SECRET_ARN ?= arn:aws:secretsmanager:eu-west-1:534526983272:secret:fastapi-staging-postgres-credentials
PRODUCTION_SECRET_ARN ?= arn:aws:secretsmanager:eu-west-1:534526983272:secret:fastapi-legacy-credentials-p9KGQI
SSH_BASTION_HOST ?= bastion.trigpointing.uk
SSH_BASTION_USER ?= ec2-user
SSH_KEY_PATH ?= ~/.ssh/trigpointing-bastion.pem
LOCAL_DB_TUNNEL_PORT ?= 5433
LOCAL_DB_TUNNEL_PORT_PROD ?= 3308
LOCAL_REDIS_TUNNEL_PORT ?= 6379
BASTION_SG_ID ?=

# Discover bastion instance id (cached per invocation) using Name tag contains 'bastion'
_bastion_instance := $(shell aws --region $(AWS_REGION) ec2 describe-instances --filters Name=tag:Name,Values='*bastion*' Name=instance-state-name,Values=running --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null)

# Start an SSH tunnel through the bastion to the staging RDS endpoint
db-tunnel-staging-start: ## Start SSH tunnel to staging RDS on localhost:$(LOCAL_DB_TUNNEL_PORT)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found. Install and configure AWS credentials."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found. Please install jq."; exit 1; }
	@mkdir -p .ssh
	@echo "🔎 Fetching staging DB host/port from Secrets Manager ($(STAGING_SECRET_ARN))"
	@SECRET_JSON=$$(aws --region $(AWS_REGION) secretsmanager get-secret-value --secret-id $(STAGING_SECRET_ARN) --query SecretString --output text); \
	RDS_HOST=$$(echo "$$SECRET_JSON" | jq -r '.host'); \
	RDS_PORT=$$(echo "$$SECRET_JSON" | jq -r '.port'); \
	echo "🌐 Tunnelling 127.0.0.1:$(LOCAL_DB_TUNNEL_PORT) → $$RDS_HOST:$$RDS_PORT via $(SSH_BASTION_USER)@$(SSH_BASTION_HOST)"; \
	# Quick connectivity pre-check to bastion (non-interactive)
	ssh -i $(SSH_KEY_PATH) -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) 'exit' 2>/dev/null || { \
	  echo "❌ Unable to reach $(SSH_BASTION_HOST) via SSH. Check: SSH_KEY_PATH, IP allowlist/Security Group, and network."; \
	  echo "   You can test manually: ssh -i $(SSH_KEY_PATH) $(SSH_BASTION_USER)@$(SSH_BASTION_HOST)"; \
	  exit 1; \
	}; \
	: # Reuse an existing control socket if present; otherwise create it and forward the port \
	if ssh -S .ssh/fastapi-staging-tunnel -O check $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) 2>/dev/null; then \
	  echo "✅ Tunnel already running"; \
	else \
	  ssh -i $(SSH_KEY_PATH) -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new -M -S .ssh/fastapi-staging-tunnel -f -N \
	    -L 127.0.0.1:$(LOCAL_DB_TUNNEL_PORT):$$RDS_HOST:$$RDS_PORT \
	    $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) && echo "✅ Tunnel started"; \
	fi

# Stop the SSH tunnel
db-tunnel-staging-stop: ## Stop SSH tunnel to staging RDS if running
	@ssh -S .ssh/fastapi-staging-tunnel -O exit $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) 2>/dev/null || true
	@rm -f .ssh/fastapi-staging-tunnel
	@echo "🛑 Tunnel stopped (if it was running)"

# Run FastAPI locally with live reload, using staging credentials via the tunnel
run-staging: ## Run FastAPI locally against staging DB (requires db-tunnel-staging-start)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found. Install and configure AWS credentials."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found. Please install jq."; exit 1; }
	@SECRET_JSON=$$(aws --region $(AWS_REGION) secretsmanager get-secret-value --secret-id $(STAGING_SECRET_ARN) --query SecretString --output text); \
	DB_USER=$$(echo "$$SECRET_JSON" | jq -r '.username'); \
	DB_PASSWORD=$$(echo "$$SECRET_JSON" | jq -r '.password'); \
	DB_NAME=$$(echo "$$SECRET_JSON" | jq -r '.dbname // .database'); \
	echo "🚀 Starting FastAPI with hot reload on http://127.0.0.1:8000"; \
	echo "💡 Note: If using Redis tunnel, make sure redis-tunnel-staging-ssm-start is running"; \
	. venv/bin/activate && \
	ENVIRONMENT=development \
	DB_HOST=127.0.0.1 DB_PORT=$(LOCAL_DB_TUNNEL_PORT) \
	DB_USER="$$DB_USER" DB_PASSWORD="$$DB_PASSWORD" DB_NAME="$$DB_NAME" \
	REDIS_URL=redis://127.0.0.1:$(LOCAL_REDIS_TUNNEL_PORT) \
	uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Open a MySQL client to staging via the tunnel
mysql-staging: ## Open MySQL client against staging via tunnel (requires db-tunnel-staging-start)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found. Install and configure AWS credentials."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found. Please install jq."; exit 1; }
	@command -v mysql >/dev/null 2>&1 || { echo "❌ mysql client not found. Install mysql-client."; exit 1; }
	@SECRET_JSON=$$(aws --region $(AWS_REGION) secretsmanager get-secret-value --secret-id $(STAGING_SECRET_ARN) --query SecretString --output text); \
	DB_USER=$$(echo "$$SECRET_JSON" | jq -r '.username'); \
	DB_PASSWORD=$$(echo "$$SECRET_JSON" | jq -r '.password'); \
	DB_NAME=$$(echo "$$SECRET_JSON" | jq -r '.dbname // .database'); \
	echo "🐬 Connecting mysql to 127.0.0.1:$(LOCAL_DB_TUNNEL_PORT) as $$DB_USER to $$DB_NAME"; \
	mysql -h 127.0.0.1 -P $(LOCAL_DB_TUNNEL_PORT) -u "$$DB_USER" -p"$$DB_PASSWORD" "$$DB_NAME"

# ---------------------------------------------------------------------------
# Production Database Access
# ---------------------------------------------------------------------------

# Start an SSH tunnel through the bastion to the PRODUCTION RDS endpoint
db-tunnel-production-start: ## Start SSH tunnel to production RDS on localhost:$(LOCAL_DB_TUNNEL_PORT_PROD)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found. Install and configure AWS credentials."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found. Please install jq."; exit 1; }
	@mkdir -p .ssh
	@echo "🔎 Fetching production DB host/port from Secrets Manager ($(PRODUCTION_SECRET_ARN))"
	@SECRET_JSON=$$(aws --region $(AWS_REGION) secretsmanager get-secret-value --secret-id $(PRODUCTION_SECRET_ARN) --query SecretString --output text); \
	RDS_HOST=$$(echo "$$SECRET_JSON" | jq -r '.host'); \
	RDS_PORT=$$(echo "$$SECRET_JSON" | jq -r '.port'); \
	echo "🌐 Tunnelling 127.0.0.1:$(LOCAL_DB_TUNNEL_PORT_PROD) → $$RDS_HOST:$$RDS_PORT via $(SSH_BASTION_USER)@$(SSH_BASTION_HOST)"; \
	ssh -i $(SSH_KEY_PATH) -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) 'exit' 2>/dev/null || { \
	  echo "❌ Unable to reach $(SSH_BASTION_HOST) via SSH. Check: SSH_KEY_PATH, IP allowlist/Security Group, and network."; \
	  exit 1; \
	}; \
	if ssh -S .ssh/fastapi-production-tunnel -O check $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) 2>/dev/null; then \
	  echo "✅ Tunnel already running"; \
	else \
	  ssh -i $(SSH_KEY_PATH) -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new -M -S .ssh/fastapi-production-tunnel -f -N \
	    -L 127.0.0.1:$(LOCAL_DB_TUNNEL_PORT_PROD):$$RDS_HOST:$$RDS_PORT \
	    $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) && echo "✅ Tunnel started"; \
	fi

# Stop the production SSH tunnel
db-tunnel-production-stop: ## Stop SSH tunnel to production RDS if running
	@ssh -S .ssh/fastapi-production-tunnel -O exit $(SSH_BASTION_USER)@$(SSH_BASTION_HOST) 2>/dev/null || true
	@rm -f .ssh/fastapi-production-tunnel
	@echo "🛑 Production tunnel stopped (if it was running)"

# Open a MySQL client to PRODUCTION via the tunnel
mysql-production: ## Open MySQL client against PRODUCTION via tunnel (requires db-tunnel-production-start)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found. Install and configure AWS credentials."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found. Please install jq."; exit 1; }
	@command -v mysql >/dev/null 2>&1 || { echo "❌ mysql client not found. Install mysql-client."; exit 1; }
	@SECRET_JSON=$$(aws --region $(AWS_REGION) secretsmanager get-secret-value --secret-id $(PRODUCTION_SECRET_ARN) --query SecretString --output text); \
	DB_USER=$$(echo "$$SECRET_JSON" | jq -r '.username'); \
	DB_PASSWORD=$$(echo "$$SECRET_JSON" | jq -r '.password'); \
	DB_NAME=$$(echo "$$SECRET_JSON" | jq -r '.dbname // .database'); \
	echo "🐬 Connecting mysql to PRODUCTION at 127.0.0.1:$(LOCAL_DB_TUNNEL_PORT_PROD) as $$DB_USER to $$DB_NAME"; \
	echo "⚠️  WARNING: You are connecting to the PRODUCTION database!"; \
	mysql -h 127.0.0.1 -P $(LOCAL_DB_TUNNEL_PORT_PROD) -u "$$DB_USER" -p"$$DB_PASSWORD" "$$DB_NAME"

# ---------------------------------------------------------------------------
# SSM-based alternatives (no public SSH required)
# ---------------------------------------------------------------------------

bastion-ssm-shell: ## Start interactive shell on bastion over SSM (no SSH ingress needed)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@[ -n "$(_bastion_instance)" ] || { echo "❌ Could not find running bastion instance."; exit 1; }
	@echo "🔐 Starting SSM shell to $(_bastion_instance)"
	aws --region $(AWS_REGION) ssm start-session --target "$(_bastion_instance)"

db-tunnel-staging-ssm-start: ## Start SSM remote host port forward to RDS → localhost:$(LOCAL_DB_TUNNEL_PORT)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found."; exit 1; }
	@[ -n "$(_bastion_instance)" ] || { echo "❌ Could not find running bastion instance."; exit 1; }
	@SECRET_JSON=$$(aws --region $(AWS_REGION) secretsmanager get-secret-value --secret-id $(STAGING_SECRET_ARN) --query SecretString --output text); \
	RDS_HOST=$$(echo "$$SECRET_JSON" | jq -r '.host'); \
	echo "🔐 SSM forwarding: 127.0.0.1:$(LOCAL_DB_TUNNEL_PORT) → $$RDS_HOST:3306 via $(_bastion_instance)"; \
	aws --region $(AWS_REGION) ssm start-session \
	  --target "$(_bastion_instance)" \
	  --document-name AWS-StartPortForwardingSessionToRemoteHost \
	  --parameters "host=[$$RDS_HOST],portNumber=['3306'],localPortNumber=['$(LOCAL_DB_TUNNEL_PORT)']"

postgres-tunnel-staging-ssm-start: ## Start SSM remote host port forward to PostgreSQL RDS → localhost:5433
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found."; exit 1; }
	@[ -n "$(_bastion_instance)" ] || { echo "❌ Could not find running bastion instance."; exit 1; }
	@SECRET_JSON=$$(aws --region $(AWS_REGION) secretsmanager get-secret-value --secret-id fastapi-staging-postgres-credentials --query SecretString --output text); \
	RDS_HOST=$$(echo "$$SECRET_JSON" | jq -r '.host'); \
	RDS_PORT=$$(echo "$$SECRET_JSON" | jq -r '.port'); \
	echo "🔐 SSM forwarding: 127.0.0.1:5433 → $$RDS_HOST:$$RDS_PORT via $(_bastion_instance)"; \
	aws --region $(AWS_REGION) ssm start-session \
	  --target "$(_bastion_instance)" \
	  --document-name AWS-StartPortForwardingSessionToRemoteHost \
	  --parameters "host=[$$RDS_HOST],portNumber=['$$RDS_PORT'],localPortNumber=['5433']"

redis-tunnel-staging-ssm-start: ## Start SSM remote host port forward to Valkey → localhost:$(LOCAL_REDIS_TUNNEL_PORT)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@[ -n "$(_bastion_instance)" ] || { echo "❌ Could not find running bastion instance."; exit 1; }
	@echo "🔎 Fetching Valkey endpoint from Terraform outputs"
	@cd terraform/common && terraform init -backend-config=backend.conf >/dev/null 2>&1 || true
	@VALKEY_HOST=$$(cd terraform/common && terraform output -raw valkey_endpoint 2>/dev/null); \
	VALKEY_PORT=$$(cd terraform/common && terraform output -raw valkey_port 2>/dev/null || echo "6379"); \
	if [ -z "$$VALKEY_HOST" ] || [ "$$VALKEY_HOST" = "" ]; then \
	  echo "❌ Could not fetch Valkey endpoint from Terraform. Make sure common infrastructure is deployed."; \
	  exit 1; \
	fi; \
	echo "🔐 SSM forwarding: 127.0.0.1:$(LOCAL_REDIS_TUNNEL_PORT) → $$VALKEY_HOST:$$VALKEY_PORT via $(_bastion_instance)"; \
	aws --region $(AWS_REGION) ssm start-session \
	  --target "$(_bastion_instance)" \
	  --document-name AWS-StartPortForwardingSessionToRemoteHost \
	  --parameters "host=[$$VALKEY_HOST],portNumber=['$$VALKEY_PORT'],localPortNumber=['$(LOCAL_REDIS_TUNNEL_PORT)']"

redis-cli-staging: ## Open redis-cli against staging via tunnel (requires redis-tunnel-staging-ssm-start)
	@command -v redis-cli >/dev/null 2>&1 || { echo "❌ redis-cli not found. Install redis-tools: sudo apt install redis-tools"; exit 1; }
	@echo "🔗 Connecting redis-cli to 127.0.0.1:$(LOCAL_REDIS_TUNNEL_PORT)"
	@echo "💡 Common commands: KEYS *, GET key, SET key value, DEL key, FLUSHDB, INFO, PING"
	redis-cli -h 127.0.0.1 -p $(LOCAL_REDIS_TUNNEL_PORT)

# ---------------------------------------------------------------------------
# Security Group helpers for dynamic admin IP (SSH) with Terraform ignore_changes
# ---------------------------------------------------------------------------

bastion-allow-my-ip: ## Add current public IP (/32) to bastion SG for SSH; set BASTION_SG_ID to override autodetect
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@MYIP=$$(curl -s https://ifconfig.me); \
	SG_ID=$${BASTION_SG_ID:-$$(aws --region $(AWS_REGION) ec2 describe-security-groups --filters Name=group-name,Values=fastapi-bastion-sg --query 'SecurityGroups[0].GroupId' --output text)}; \
	[ -n "$$SG_ID" ] || { echo "❌ Could not determine bastion SG id"; exit 1; }; \
	echo "🔓 Authorising $$MYIP/32 on $$SG_ID"; \
	aws --region $(AWS_REGION) ec2 authorize-security-group-ingress --group-id "$$SG_ID" --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges='[{CidrIp="'$$MYIP'/32",Description="Admin dynamic IP"}]' || true

bastion-revoke-my-ip: ## Remove current public IP (/32) from bastion SG ingress
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@MYIP=$$(curl -s https://ifconfig.me); \
	SG_ID=$${BASTION_SG_ID:-$$(aws --region $(AWS_REGION) ec2 describe-security-groups --filters Name=group-name,Values=fastapi-bastion-sg --query 'SecurityGroups[0].GroupId' --output text)}; \
	[ -n "$$SG_ID" ] || { echo "❌ Could not determine bastion SG id"; exit 1; }; \
	echo "🔒 Revoking $$MYIP/32 from $$SG_ID"; \
	aws --region $(AWS_REGION) ec2 revoke-security-group-ingress --group-id "$$SG_ID" --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges='[{CidrIp="'$$MYIP'/32"}]' || true

ecs-exec-phpbb: ## Open a shell in the first running phpBB ECS task (requires ECS Exec + SSM perms)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@echo "🔎 Enabling ECS Exec on service (idempotent)"; \
	aws ecs update-service --region $(AWS_REGION) --cluster trigpointing-cluster --service trigpointing-phpbb-common --enable-execute-command >/dev/null 2>&1 || true; \
	TASK_ARN=$$(aws ecs list-tasks --region $(AWS_REGION) --cluster trigpointing-cluster --service-name trigpointing-phpbb-common --desired-status RUNNING --query 'taskArns[0]' --output text); \
	[ "$$TASK_ARN" != "None" ] && [ -n "$$TASK_ARN" ] || { echo "❌ No running phpBB task found"; exit 1; }; \
	echo "🖥️  Executing shell on $$TASK_ARN"; \
	aws ecs execute-command --region $(AWS_REGION) --cluster trigpointing-cluster --task "$$TASK_ARN" --container trigpointing-phpbb --interactive --command "/bin/bash"

ecs-exec-mediawiki: ## Open a shell in the first running mediawiki ECS task (requires ECS Exec + SSM perms)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@echo "🔎 Enabling ECS Exec on service (idempotent)"; \
	aws ecs update-service --region $(AWS_REGION) --cluster trigpointing-cluster --service trigpointing-mediawiki-common --enable-execute-command >/dev/null 2>&1 || true; \
	TASK_ARN=$$(aws ecs list-tasks --region $(AWS_REGION) --cluster trigpointing-cluster --service-name trigpointing-mediawiki-common --desired-status RUNNING --query 'taskArns[0]' --output text); \
	[ "$$TASK_ARN" != "None" ] && [ -n "$$TASK_ARN" ] || { echo "❌ No running mediawiki task found"; exit 1; }; \
	echo "🖥️  Executing shell on $$TASK_ARN"; \
	aws ecs execute-command --region $(AWS_REGION) --cluster trigpointing-cluster --task "$$TASK_ARN" --container trigpointing-mediawiki --interactive --command "/bin/bash"

# Development setup
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test-db-start: ## Start local PostgreSQL test database
	@docker-compose -f docker-compose.test.yml up -d
	@echo "⏳ Waiting for PostgreSQL to be ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if docker-compose -f docker-compose.test.yml exec -T test-db pg_isready -U test_user -d test_db > /dev/null 2>&1; then \
			echo "✅ Test database ready on localhost:5432"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "✅ Test database ready on localhost:5432"

test-db-stop: ## Stop local PostgreSQL test database
	docker-compose -f docker-compose.test.yml down -v

test: ## Run tests (requires test-db-start)
	@docker-compose -f docker-compose.test.yml ps test-db | grep -q "Up" || { echo "❌ Test database not running. Run 'make test-db-start' first."; exit 1; }
	CACHE_ENABLED=false pytest -n auto

test-cov: ## Run tests with coverage
	CACHE_ENABLED=false pytest -n auto
	pytest --cov=api --cov-report=term-missing --cov-report=html --cov-report=xml:coverage.xml

diff-cov: ## Check diff coverage against origin/main (fail if < 90%)
	@if [ ! -f coverage.xml ]; then \
		echo "Generating coverage.xml via pytest..."; \
		pytest --cov=api --cov-report=xml:coverage.xml >/dev/null; \
	fi
	@BASE_REF=$$(git merge-base HEAD origin/main); \
	echo "Comparing coverage against $$BASE_REF"; \
	diff-cover coverage.xml --compare-branch $$BASE_REF --fail-under=50

# Code quality
lint: ## Run linting
	flake8 api
	mypy api --ignore-missing-imports

format: ## Format code
	black api
	isort api
	terraform fmt -recursive terraform/

format-check: ## Check code formatting
	black --check api
	isort --check-only api

type-check: ## Run type checking
	mypy api --ignore-missing-imports

security: ## Run security checks
	bandit -r api --skip B101 --exclude api/tests
	-safety check

# Database migrations with Alembic
migration-create: ## Create a new migration (usage: make migration-create MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Error: MSG parameter required"; \
		echo "Usage: make migration-create MSG=\"your migration description\""; \
		exit 1; \
	fi
	@echo "🔧 Creating new migration: $(MSG)"
	alembic revision --autogenerate -m "$(MSG)"
	@echo "✅ Migration created. Review the file in alembic/versions/ before applying"

migration-upgrade: ## Apply all pending migrations locally
	@echo "⬆️  Applying migrations..."
	alembic upgrade head
	@echo "✅ Migrations applied"

migration-downgrade: ## Rollback one migration locally
	@echo "⬇️  Rolling back one migration..."
	alembic downgrade -1
	@echo "✅ Migration rolled back"

migration-history: ## Show migration history
	@echo "📜 Migration history:"
	alembic history --verbose

migration-current: ## Show current migration revision
	@echo "📍 Current revision:"
	alembic current --verbose

migration-check: ## Check if database is up to date (exits 1 if pending migrations)
	@CURRENT=$$(alembic current 2>&1 | grep -o '[a-f0-9]\{12\}' | head -1); \
	HEAD=$$(alembic heads 2>&1 | grep -o '[a-f0-9]\{12\}' | head -1); \
	if [ "$$CURRENT" = "$$HEAD" ]; then \
		echo "✅ Database is up to date ($$CURRENT)"; \
	else \
		echo "⚠️  Pending migrations detected"; \
		echo "   Current: $$CURRENT"; \
		echo "   Latest:  $$HEAD"; \
		exit 1; \
	fi

# Application
build: ## Build the application
	docker build -t platform-api .

run: ## Run the application locally
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Docker commands
docker-build: ## Build Docker image
	docker build -t platform-api .

docker-run: ## Run application with Docker Compose
	docker-compose up -d

docker-dev: ## Run application in development mode with Docker Compose
	docker-compose -f docker-compose.dev.yml up -d

docker-down: ## Stop Docker containers
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

docker-logs: ## View Docker logs
	docker-compose logs -f

# Database
db-migrate: ## Run database migrations
	alembic upgrade head

db-migration: ## Create new database migration
	alembic revision --autogenerate -m "$(msg)"

mysql-client: ## Connect to development MySQL database
	@echo "Connecting to development MySQL database..."
	@if docker-compose ps db 2>/dev/null | grep -q "Up"; then \
		echo "Using Docker Compose MySQL instance..."; \
		docker-compose exec db mysql -u fastapi_user -pfastapi_pass fastapi_db; \
	elif docker-compose -f docker-compose.dev.yml ps db 2>/dev/null | grep -q "Up"; then \
		echo "Using Docker Compose dev MySQL instance..."; \
		docker-compose -f docker-compose.dev.yml exec db mysql -u fastapi_user -pfastapi_pass fastapi_db; \
	elif command -v mysql >/dev/null 2>&1; then \
		echo "Using local MySQL client with connection details from environment..."; \
		if [ -f .env ]; then \
			export $$(grep -v '^#' .env | xargs); \
			mysql -h localhost -P 3306 -u fastapi_user -pfastapi_pass fastapi_db; \
		else \
			mysql -h localhost -P 3306 -u fastapi_user -pfastapi_pass fastapi_db; \
		fi; \
	else \
		echo "❌ Error: No MySQL connection available."; \
		echo "Please ensure either:"; \
		echo "  1. Docker Compose is running: make docker-dev"; \
		echo "  2. MySQL client is installed: apt install mysql-client"; \
		exit 1; \
	fi

# Cleanup
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f test_gw*.db test.db
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info

# Terraform commands
tf-init: ## Initialize Terraform with environment-specific backend (usage: make tf-init env=staging)
	cd terraform && terraform init -backend-config="backend-$(env).conf"

tf-plan: ## Plan Terraform changes (usage: make tf-plan env=staging)
	@if [ ! -f "terraform/cloudflare-cert-trigpointing-$(shell echo $(env) | sed 's/staging/me/;s/production/uk/').tfvars" ]; then \
		echo "🔑 CloudFlare certificate file not found. Using base configuration only..."; \
		cd terraform && terraform plan -var-file="$(env).tfvars"; \
	else \
		echo "🔑 Using CloudFlare certificates for $(env)..."; \
		cd terraform && terraform plan -var-file="$(env).tfvars" -var-file="cloudflare-cert-trigpointing-$(shell echo $(env) | sed 's/staging/me/;s/production/uk/').tfvars"; \
	fi

tf-apply: ## Apply Terraform changes (usage: make tf-apply env=staging)
	@if [ ! -f "terraform/cloudflare-cert-trigpointing-$(shell echo $(env) | sed 's/staging/me/;s/production/uk/').tfvars" ]; then \
		echo "🔑 CloudFlare certificate file not found. Using base configuration only..."; \
		cd terraform && terraform apply -var-file="$(env).tfvars"; \
	else \
		echo "🔑 Using CloudFlare certificates for $(env)..."; \
		cd terraform && terraform apply -var-file="$(env).tfvars" -var-file="cloudflare-cert-trigpointing-$(shell echo $(env) | sed 's/staging/me/;s/production/uk/').tfvars"; \
	fi

tf-destroy: ## Destroy Terraform infrastructure (usage: make tf-destroy env=staging)
	@if [ ! -f "terraform/cloudflare-cert-trigpointing-$(shell echo $(env) | sed 's/staging/me/;s/production/uk/').tfvars" ]; then \
		echo "🔑 CloudFlare certificate file not found. Using base configuration only..."; \
		cd terraform && terraform destroy -var-file="$(env).tfvars"; \
	else \
		echo "🔑 Using CloudFlare certificates for $(env)..."; \
		cd terraform && terraform destroy -var-file="$(env).tfvars" -var-file="cloudflare-cert-trigpointing-$(shell echo $(env) | sed 's/staging/me/;s/production/uk/').tfvars"; \
	fi

tf-validate: ## Validate Terraform configuration
	cd terraform && terraform validate

tf-fmt: ## Format Terraform files
	cd terraform && terraform fmt -recursive

# CI/CD
pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

ci: terraform-format-check test-db-start format-check lint type-check security test web-lint web-type-check web-test test-db-stop ## Run all CI checks

# Web application targets
web-install: ## Install web application dependencies
	cd web && npm ci

web-dev: ## Run web application in development mode
	cd web && npm run dev

web-build: ## Build web application for production
	cd web && npm run build

web-test: ## Run web application tests
	cd web && npm run test:run

web-lint: ## Lint web application code
	cd web && npm run lint

web-type-check: ## Type check web application
	cd web && npm run type-check

terraform-format-check: ## Check Terraform formatting; auto-format and fail if mismatches
	@command -v terraform >/dev/null 2>&1 || { echo "❌ terraform not installed. Please install Terraform to run formatting checks."; exit 1; }
	@echo "🔎 Checking Terraform formatting..."
	@cd terraform && terraform fmt -check -recursive .
	@if [ $$? -ne 0 ]; then \
	  echo "⚠️  Terraform files need formatting. Applying formatting..."; \
	  (cd terraform && terraform fmt -recursive .); \
	  echo "❌ Formatting changes applied. Commit the changes and re-run CI."; \
	  exit 1; \
	else \
	  echo "✅ Terraform formatting is correct."; \
	fi
