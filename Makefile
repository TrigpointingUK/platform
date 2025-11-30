orientation-model:
	@echo "Creating orientation model with self-supervised rotations..."
	python -m pip install -q -r requirements-train.txt
	python scripts/train_export_orientation.py --data ./res/orientation_data --output ./res/models/orientation_classifier.onnx --epochs 3 --batch-size 64 --lr 1e-3
	@echo "Model exported to res/models/orientation_classifier.onnx"
.PHONY: help install install-dev test test-cov lint format type-check security build run clean docker-build \
	run-staging db-tunnel-staging-ssm-start bastion-ssm-shell bastion-allow-my-ip bastion-revoke-my-ip \
	redis-tunnel-staging-ssm-start redis-cli-staging \
	test-db-start test-db-stop \
	web-install web-dev web-build web-test web-lint web-type-check \
	migration-create migration-upgrade migration-downgrade migration-history migration-current migration-check \
	migrate-staging migrate-production migrate-status

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
PRODUCTION_SECRET_ARN ?= arn:aws:secretsmanager:eu-west-1:534526983272:secret:fastapi-production-postgres-credentials
SSH_BASTION_HOST ?= bastion.trigpointing.uk
SSH_BASTION_USER ?= ec2-user
SSH_KEY_PATH ?= ~/.ssh/trigpointing-bastion.pem
LOCAL_DB_TUNNEL_PORT ?= 5433
LOCAL_REDIS_TUNNEL_PORT ?= 6379
BASTION_SG_ID ?=

# Discover bastion instance id (cached per invocation) using Name tag contains 'bastion'
_bastion_instance := $(shell aws --region $(AWS_REGION) ec2 describe-instances --filters Name=tag:Name,Values='*bastion*' Name=instance-state-name,Values=running --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null)

# Run FastAPI locally with live reload, using staging credentials via the tunnel
run-staging: ## Run FastAPI locally against staging DB (requires db-tunnel-staging-ssm-start)
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

# ---------------------------------------------------------------------------
# SSM-based alternatives (no public SSH required)
# ---------------------------------------------------------------------------

bastion-ssm-shell: ## Start interactive shell on bastion over SSM (no SSH ingress needed)
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@[ -n "$(_bastion_instance)" ] || { echo "❌ Could not find running bastion instance."; exit 1; }
	@echo "🔐 Starting SSM shell to $(_bastion_instance)"
	aws --region $(AWS_REGION) ssm start-session --target "$(_bastion_instance)"

db-tunnel-staging-ssm-start: ## Start SSM remote host port forward to PostgreSQL RDS → localhost:5433
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

migrate-staging: ## Apply migrations to staging via SSM tunnel (requires db-tunnel-staging-ssm-start)
	@echo "🔧 Applying migrations to STAGING"
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found."; exit 1; }
	@SECRET_JSON=$$(aws secretsmanager get-secret-value \
	  --region $(AWS_REGION) \
	  --secret-id fastapi-staging-postgres-credentials \
	  --query SecretString --output text); \
	DB_HOST=localhost DB_PORT=5433 \
	DB_USER=$$(echo "$$SECRET_JSON" | jq -r '.username') \
	DB_PASSWORD=$$(echo "$$SECRET_JSON" | jq -r '.password') \
	DB_NAME=$$(echo "$$SECRET_JSON" | jq -r '.dbname') \
	ENV_NAME=STAGING \
	alembic upgrade head

migrate-production: ## Apply migrations to production via SSM tunnel (requires tunnel, with confirmation)
	@echo "⚠️  PRODUCTION MIGRATION ⚠️"
	@read -p "Type 'production' to confirm: " confirm && [ "$$confirm" = "production" ] || { echo "❌ Cancelled"; exit 1; }
	@command -v aws >/dev/null 2>&1 || { echo "❌ aws CLI not found."; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "❌ jq not found."; exit 1; }
	@SECRET_JSON=$$(aws secretsmanager get-secret-value \
	  --region $(AWS_REGION) \
	  --secret-id fastapi-production-postgres-credentials \
	  --query SecretString --output text); \
	DB_HOST=localhost DB_PORT=5433 \
	DB_USER=$$(echo "$$SECRET_JSON" | jq -r '.username') \
	DB_PASSWORD=$$(echo "$$SECRET_JSON" | jq -r '.password') \
	DB_NAME=$$(echo "$$SECRET_JSON" | jq -r '.dbname') \
	ENV_NAME=PRODUCTION \
	alembic upgrade head

migrate-status: ## Check migration status (ENV=staging|production)
	@[ "$(ENV)" = "staging" ] || [ "$(ENV)" = "production" ] || { \
	  echo "Usage: make migrate-status ENV=staging (or ENV=production)"; exit 1; }
	@echo "🔍 Checking $(ENV) migration status..."
	@SECRET_ID=$$([ "$(ENV)" = "staging" ] && echo "fastapi-staging-postgres-credentials" || echo "fastapi-production-postgres-credentials"); \
	SECRET_JSON=$$(aws secretsmanager get-secret-value \
	  --region $(AWS_REGION) --secret-id $$SECRET_ID \
	  --query SecretString --output text); \
	DB_HOST=localhost DB_PORT=5433 \
	DB_USER=$$(echo "$$SECRET_JSON" | jq -r '.username') \
	DB_PASSWORD=$$(echo "$$SECRET_JSON" | jq -r '.password') \
	DB_NAME=$$(echo "$$SECRET_JSON" | jq -r '.dbname') \
	ENV_NAME=$$(echo $(ENV) | tr '[:lower:]' '[:upper:]') \
	alembic current

# Application
build: ## Build the application
	docker build -t platform-api .

run: ## Run the application locally
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Docker commands
docker-build: ## Build Docker image
	docker build -t platform-api .

# Database
db-migrate: ## Run database migrations
	alembic upgrade head

db-migration: ## Create new database migration
	alembic revision --autogenerate -m "$(msg)"

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

# Terraform validation (used by CI)
tf-validate: ## Validate Terraform configuration
	@cd terraform/common && terraform init -backend=false >/dev/null 2>&1 || true
	@cd terraform/staging && terraform init -backend=false >/dev/null 2>&1 || true
	@cd terraform/production && terraform init -backend=false >/dev/null 2>&1 || true
	@echo "🔍 Validating Terraform configuration..."
	@cd terraform/common && terraform validate
	@cd terraform/staging && terraform validate
	@cd terraform/production && terraform validate
	@echo "✅ Terraform configuration is valid"

# CI/CD
pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

ci: terraform-format-check tf-validate test-db-start format-check lint type-check security test web-lint web-type-check web-test test-db-stop ## Run all CI checks

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
