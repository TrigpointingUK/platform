# Trigpointing Platform - API Documentation

> **Note:** This is the API component documentation. For the overall platform overview, see the [main README](../README.md).

A modern FastAPI-based API to gradually migrate the 20-year-old PHP/MySQL website to a contemporary architecture. The API provides a secure, scalable foundation with JWT authentication, comprehensive testing, and AWS Fargate deployment.

## 🚀 Features

- **Modern FastAPI Framework**: High-performance Python web framework
- **JWT Authentication**: Secure token-based authentication
- **MySQL Integration**: Direct connection to your existing legacy database
- **Comprehensive Testing**: Full test coverage with pytest
- **Docker Support**: Easy containerization and deployment
- **AWS Fargate Ready**: Production-ready infrastructure with Terraform
- **CI/CD Pipeline**: GitHub Actions for automated testing and deployment
- **Security Best Practices**: Input validation, SQL injection protection, and more

## 📋 API Endpoints

### Public Endpoints

- `GET /api/v1/tlog/trig-count/{trig_id}` - Get count of tlog entries for a trigger ID

### Protected Endpoints (JWT Required)

- `POST /api/v1/auth/login` - Authenticate and get JWT token
- `GET /api/v1/users/email/{user_id}` - Get user email (own email or admin required)

### Health & Documentation

- `GET /health` - Health check endpoint
- `GET /api/v1/openapi.json` - OpenAPI specification
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd platform
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   make install-dev
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your database credentials and secrets
   ```

5. **Start with Docker Compose (Recommended)**
   ```bash
   make docker-dev
   ```

   Or run manually:
   ```bash
   make run
   ```

6. **Access the application**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Database Setup

The Docker Compose setup includes a MySQL container with sample data. For connecting to your existing database:

1. Update the `DATABASE_URL` in your `.env` file:
   ```
   DATABASE_URL=mysql+pymysql://user:password@host:port/database
   ```

2. Ensure your existing database has the required tables:
   - `user` table with columns: `user_id`, `email`, `password_hash`, `admin_ind`
   - `tlog` table with columns: `id`, `trig_id`, and other legacy columns

## 🔍 Code Quality Requirements (CRITICAL)

**🚨 MANDATORY: Strict CI validation enforced on main/develop branches!**

### Branch Protection Rules

#### For `main` and `develop` branches:
- **Pre-push validation** automatically enforced via git hooks
- **ALL CI checks** must pass before any push is allowed
- **NO EXCEPTIONS** - push will be blocked if CI fails

```bash
# REQUIRED before every push to main/develop
make ci
```

#### Quick validation check:
```bash
# Verify everything passes before pushing
source venv/bin/activate && make ci
```

### Quick Setup with Automation
```bash
# One-time setup: environment, dependencies, and automated git hooks
chmod +x setup-dev.sh && ./setup-dev.sh
```

### Manual Process (if not using setup script)
```bash
# 1. Activate virtual environment (required)
source venv/bin/activate

# 2. Run complete CI suite before every commit
make ci

# 3. Only commit if all checks pass ✅
git add . && git commit -m "your message"
```

### What `make ci` checks:
- ✅ **black** - Code formatting (`black --check app tests`)
- ✅ **isort** - Import sorting (`isort --check-only app tests`)
- ✅ **flake8** - Code linting (`flake8 app tests`)
- ✅ **mypy** - Type checking (`mypy app --ignore-missing-imports`)
- ✅ **bandit** - Security scanning (`bandit -r app`)
- ⚠️ **safety** - Dependency vulnerabilities (`safety check` - warnings allowed)
- ✅ **pytest** - Full test suite (all tests must pass)

### Git Hooks Enforcement:
- **Pre-commit hook**: Runs `make ci` on every commit
- **Pre-push hook**: Blocks pushes to main/develop if CI fails
- **Automatic installation**: Hooks installed via `./setup-dev.sh`

### Manual CI fix workflow (if CI fails):
```bash
# Auto-fix formatting and imports
black app tests && isort app tests

# Check remaining issues
flake8 app tests                    # Fix linting errors
mypy app --ignore-missing-imports   # Fix type errors
pytest                             # Fix failing tests

# Final validation (must pass)
make ci
```

**Automated enforcement:** The pre-commit hook automatically runs these checks on every commit.

## 🧪 Testing

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
pytest tests/test_auth.py -v
```

## 🔍 Code Quality

```bash
# Format code
make format

# Check formatting
make format-check

# Run linting
make lint

# Type checking
make type-check

# Security checks
make security

# Run all CI checks
make ci
```

## 🐳 Docker

### Development
```bash
# Start development environment
make docker-dev

# View logs
make docker-logs

# Stop containers
make docker-down
```

### Production
```bash
# Build production image
make docker-build

# Run production setup
make docker-run
```

## ☁️ AWS Deployment

### Overview

Infrastructure is managed with Terraform and organized by environment:
- `terraform/common/` - Shared resources (VPC, bastion, RDS PostgreSQL, Valkey, etc.)
- `terraform/staging/` - Staging-specific resources (API, SPA)
- `terraform/production/` - Production-specific resources (API, SPA)

### Prerequisites

1. AWS CLI configured (`aws configure`)
2. Terraform installed (`brew install terraform` or from [terraform.io](https://terraform.io))
3. S3 bucket for Terraform state (already configured in backend.conf files)

### Deployment Workflow

#### Option 1: Using deploy.sh (Automated)

The `scripts/deploy.sh` script handles Docker builds and Terraform deployment:

```bash
# Deploy to staging
./scripts/deploy.sh staging

# Deploy to production (requires confirmation)
./scripts/deploy.sh production
```

**Note:** This script may need updates for your specific Docker registry and infrastructure setup.

#### Option 2: Manual Terraform Deployment

For infrastructure-only changes or more granular control:

**Common Infrastructure (VPC, RDS, Bastion):**
```bash
cd terraform/common
terraform init -backend-config=backend.conf
terraform plan
terraform apply
```

**Staging Environment:**
```bash
cd terraform/staging
terraform init -backend-config=backend.conf
terraform plan
terraform apply
```

**Production Environment:**
```bash
cd terraform/production
terraform init -backend-config=backend.conf
terraform plan
terraform apply
```

### Terraform Validation and Formatting

```bash
# Validate all configurations (from project root)
make tf-validate

# Check formatting (used by CI)
make terraform-format-check

# Auto-format all Terraform files
terraform fmt -recursive terraform/
```

### Infrastructure Components

Current infrastructure (PostgreSQL + Valkey):

- **VPC**: Multi-AZ setup with public/private subnets
- **ECS Fargate**: Serverless container hosting for API, SPA, Forum, Wiki
- **Application Load Balancer**: High availability load balancing with OIDC authentication
- **RDS PostgreSQL**: Managed PostgreSQL database with PostGIS extension
- **Valkey (Redis)**: ElastiCache-compatible caching layer
- **CloudWatch**: Monitoring, logging, and alarms
- **Bastion Host**: Secure access to private resources
- **CloudFront/CloudFlare**: CDN and edge security

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL connection string | Required |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Required |
| `JWT_ALGORITHM` | JWT signing algorithm | HS256 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | 30 |
| `DEBUG` | Enable debug mode | false |
| `API_V1_STR` | API version prefix | /api/v1 |

### Database Schema

Ensure your legacy database includes these minimum required tables:

```sql
-- Users table
CREATE TABLE user (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    admin_ind CHAR(1) DEFAULT 'N' NOT NULL
);

-- TLog table
CREATE TABLE tlog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trig_id INT NOT NULL,
    -- Add your existing columns here
);
```

## 🔐 Security

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **Input Validation**: Pydantic models for request validation
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Security Headers**: Basic security headers included
- **Secrets Management**: Environment variables for sensitive data

## 📊 Monitoring

- **Health Checks**: Built-in health check endpoint
- **CloudWatch Integration**: Comprehensive logging and metrics
- **Application Metrics**: CPU, memory, and request metrics
- **Database Monitoring**: RDS performance insights
- **Alerting**: SNS alerts for critical issues

## 🔄 CI/CD

The GitHub Actions pipeline includes:

1. **Code Quality**: Linting, formatting, type checking
2. **Security Scanning**: Bandit, Trivy vulnerability scanning
3. **Testing**: Comprehensive test suite with coverage
4. **Building**: Docker image creation and registry push
5. **Deployment**: Automatic deployment to staging/production

### Required Secrets

Add these secrets to your GitHub repository:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `make ci`
5. Commit: `git commit -am 'Add feature'`
6. Push: `git push origin feature-name`
7. Create a Pull Request

## 📝 Migration Strategy

This API is designed for gradual migration:

1. **Phase 1**: Set up API alongside existing PHP application
2. **Phase 2**: Migrate critical endpoints to FastAPI
3. **Phase 3**: Update frontend to use new API endpoints
4. **Phase 4**: Gradually deprecate PHP endpoints
5. **Phase 5**: Complete migration and decommission legacy system

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Verify DATABASE_URL format
   - Check database credentials
   - Ensure database is accessible from application

2. **JWT Token Issues**
   - Verify JWT_SECRET_KEY is set
   - Check token expiration settings
   - Ensure proper Authorization header format

3. **Docker Issues**
   - Check Docker daemon is running
   - Verify port availability (8000, 3306)
   - Check container logs: `make docker-logs`

### Logs

```bash
# Application logs
docker-compose logs app

# Database logs
docker-compose logs db

# All logs
make docker-logs
```

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Ansible Setup](docs/ANSIBLE_SETUP.md)** - Infrastructure management with Ansible
- **[Database Schema](docs/database/schema_documentation.md)** - Complete database documentation
- **[Infrastructure Setup](docs/infrastructure/)** - Terraform and infrastructure configuration
- **[Security Configuration](docs/security/)** - Security best practices and setup
- **[Migration Guides](docs/migration/)** - Migration procedures and strategies

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)
- [Ansible Documentation](https://docs.ansible.com/)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
