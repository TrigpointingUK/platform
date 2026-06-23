# Trigpointing Platform

Monorepo containing all infrastructure, applications, and services for Trigpointing.uk - a 20-year-old trigpoint and surveying community website.

## Components

### Applications

- **api/** - Python FastAPI backend REST API
  - Modern Python 3.13+ API with Auth0 integration
  - Comprehensive test coverage, type checking
  - [Detailed API Documentation](docs/README-fastapi.md)

- **web/** - React Single-Page Application
  - Modern TypeScript SPA with Auth0 PKCE authentication
  - Vite for fast builds, TanStack Query for state management
  - Gradual "strangler fig" migration of legacy pages
  - [Web App Documentation](web/README.md)
  
- **forum/** - phpBB 3.3 Forum
  - Community discussion forums with Auth0 SSO
  - Custom theme and extensions
  - Docker-based deployment
  
- **wiki/** - MediaWiki Installation
  - Community-maintained documentation
  - Auth0 integration for unified authentication
  - Docker-based deployment

### Infrastructure

- **terraform/** - AWS Infrastructure as Code
  - Multi-environment (staging/production)
  - ECS Fargate, RDS MySQL, ElastiCache, CloudFront
  - Cloudflare integration
  - [Infrastructure Documentation](docs/infrastructure/)
  
- **Ansible/** - Configuration Management
  - Bastion host setup and maintenance
  - Common server configurations
  - [Ansible Documentation](docs/ansible/)

### Testing & Tools

- **locust/** - Performance and load testing
- **scripts/** - Deployment and maintenance scripts

## Architecture

- **Web SPA**: React + TypeScript (Vite) served by nginx on ECS Fargate
- **API**: FastAPI (Python 3.13) on ECS Fargate
- **Forum**: phpBB on ECS Fargate
- **Wiki**: MediaWiki on ECS Fargate
- **Database**: RDS MySQL 8.0
- **Cache**: ElastiCache (Valkey)
- **Load Balancer**: AWS ALB with path-based routing
- **CDN**: Cloudflare
- **Auth**: Auth0 with unified SSO across all services

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 20+ and npm (for web app)
- Docker & Docker Compose
- AWS CLI (for deployments)
- Terraform (for infrastructure)

### Local Development

```bash
# Clone the repository
git clone git@github.com:USERNAME/platform.git
cd platform

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# API Development - connect to shared database
make postgres-tunnel  # In one terminal
make redis-tunnel     # In another terminal
make run-staging      # Runs API against staging database

# Web App Development
cd web
npm ci
npm run dev  # Runs on http://localhost:5173

# Run all quality checks
make ci
```

See component-specific documentation for detailed setup:
- [API Setup](docs/README-fastapi.md)
- [Web App Setup](web/README.md)

## Documentation

- [API Documentation](docs/README-fastapi.md) - FastAPI backend setup and development
- [Infrastructure Setup](docs/infrastructure/) - AWS deployment and Terraform
- [Ansible Setup](docs/ANSIBLE_SETUP.md) - Configuration management
- [Local Development](docs/LOCAL_ENV.md) - Local environment setup
- [Database Schema](docs/database/schema_documentation.md) - Complete database documentation

## Deployment

The platform uses a develop → main branch workflow:

- **develop** branch deploys to staging (trigpointing.me)
- **main** branch deploys to production (trigpointing.uk)

CI/CD pipelines automatically build and deploy on push to these branches.

See [Infrastructure Documentation](docs/infrastructure/) for detailed deployment procedures.

## Development Workflow

1. All changes pushed to `develop` branch
2. CI runs tests, linting, security checks
3. Automatic deployment to staging on success
4. Manual PR to `main` for production deployment
5. Run `make ci` before committing (enforced by pre-commit hooks)

## Repository Structure

```
platform/
├── api/                 # FastAPI backend API
│   ├── api/             # API endpoints
│   ├── core/            # Core configuration
│   ├── crud/            # Database operations
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── tests/           # Unit tests
├── forum/               # phpBB deployment
├── wiki/                # MediaWiki deployment
├── terraform/           # Infrastructure as Code
│   ├── common/          # Shared infrastructure
│   ├── staging/         # Staging environment
│   ├── production/      # Production environment
│   └── modules/         # Reusable modules
├── Ansible/             # Configuration management
├── locust/              # Performance tests
├── docs/                # Documentation
└── scripts/             # Utilities
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run `make ci` to validate
5. Push to develop branch
6. Create Pull Request

## License

MIT License - see LICENSE file for details

