environment = "production"

# Use ECS Valkey instead of ElastiCache Serverless
use_ecs_valkey = true

# Container image (built by GitHub Actions CI/CD)
container_image = "ghcr.io/trigpointinguk/platform/api:main"

# Scaling settings
desired_count = 1
min_capacity  = 1
max_capacity  = 10

# Resource allocation
cpu    = 1024 # 1 vCPU (increased from 0.25 vCPU for production load)
memory = 2048 # 2GB (minimum for 1 vCPU on Fargate)

# CloudFlare SSL Configuration (REQUIRED for production)
domain_name           = "api.trigpointing.uk"
enable_cloudflare_ssl = true

log_level                = "INFO"
cors_origins             = ["https://trigpointing.uk", "https://api.trigpointing.uk", "https://preview.trigpointing.uk"]
spa_container_image      = "ghcr.io/trigpointinguk/platform/web:main"
db_pool_size             = 20 # Increased for production traffic after going live
db_pool_max_overflow     = 20 # Additional connections beyond pool_size
db_pool_recycle          = 300
profiling_enabled        = false
profiling_default_format = "html"

# Photo upload configuration
photos_s3_bucket = "trigpointinguk-photos"
photos_server_id = 1

# Auth0 Configuration
disable_signup = false
