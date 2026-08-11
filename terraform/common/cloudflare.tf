# CloudFlare zone configuration for both staging and production domains

# Data source to get zone information
data "cloudflare_zones" "staging" {
  name = "trigpointing.me"
}

data "cloudflare_zones" "production" {
  name = "trigpointing.uk"
}

# Force HTTPS: 301 redirect all HTTP requests to HTTPS at the Cloudflare edge.
# Without this, Cloudflare will happily proxy plain HTTP to our HTTPS-only origin.
resource "cloudflare_zone_setting" "always_use_https_production" {
  zone_id    = data.cloudflare_zones.production.result[0].id
  setting_id = "always_use_https"
  value      = "on"
}

resource "cloudflare_zone_setting" "always_use_https_staging" {
  zone_id    = data.cloudflare_zones.staging.result[0].id
  setting_id = "always_use_https"
  value      = "on"
}

# DNS Records
# CNAME record for staging domain
resource "cloudflare_dns_record" "api_staging" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "api"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "API endpoint for staging environment - managed by Terraform"
}

# CNAME record for production domain
resource "cloudflare_dns_record" "api_production" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "api"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "API endpoint for production environment - managed by Terraform"
}

# CNAME record for cache management interface
resource "cloudflare_dns_record" "cache" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "cache"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Redis Commander cache management interface - managed by Terraform"
}

# CNAME record for preview/smoke testing subdomain
resource "cloudflare_dns_record" "preview" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "preview"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Preview subdomain for smoke testing SPA on production infrastructure - managed by Terraform"
}

# CNAME record for bastion
resource "cloudflare_dns_record" "bastion" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "bastion"
  content = aws_eip.bastion.public_ip
  type    = "A"
  proxied = false # Enable CloudFlare proxy (orange cloud)
  ttl     = 600   # 10 minutes

  comment = "Bastion host for TrigpointingUK - managed by Terraform"
}

# Test CNAMEs for ALB testing
resource "cloudflare_dns_record" "test1" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "test1"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Test domain 1 for ALB testing - managed by Terraform"
}

resource "cloudflare_dns_record" "test2" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "test2"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Test domain 2 for ALB testing - managed by Terraform"
}

# Production CNAMEs for trigpointing.uk domains
resource "cloudflare_dns_record" "forum" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "forum"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Forum subdomain for TrigpointingUK - managed by Terraform"
}

resource "cloudflare_dns_record" "phpmyadmin" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "phpmyadmin"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "phpMyAdmin subdomain for TrigpointingUK - managed by Terraform"
}

resource "cloudflare_dns_record" "pgadmin" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "pgadmin"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "pgAdmin subdomain for TrigpointingUK - managed by Terraform"
}

resource "cloudflare_dns_record" "metabase_production" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "data"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true
  ttl     = 1

  comment = "Metabase data exploration for TrigpointingUK - managed by Terraform"
}

resource "cloudflare_dns_record" "metabase_staging" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "data"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true
  ttl     = 1

  comment = "Metabase data exploration for TrigpointingUK staging - managed by Terraform"
}

resource "cloudflare_dns_record" "wiki" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "wiki"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Wiki subdomain for TrigpointingUK - managed by Terraform"
}

# Photo hostnames, proxied so that image views hit the CloudFlare cache rather
# than billable S3 egress. The API previously handed out direct
# https://<bucket>.s3.amazonaws.com/... URLs, so every view by every browser and
# bot was a chargeable GetObject.
#
# These point at CloudFront rather than straight at S3. S3 resolves the bucket
# from the Host header, and rewriting that header at the CloudFlare edge needs the
# Pro-plan Host Header Override; CloudFront sets the origin Host itself. See
# photos-cdn.tf for the full rationale.
resource "cloudflare_dns_record" "photos_production" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "photos"
  content = aws_cloudfront_distribution.photos["production"].domain_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Photo CDN (CloudFront) behind CloudFlare cache - managed by Terraform"
}

# Staging uses a separate photo bucket (trigpointinguk-test, server.id = 3).
resource "cloudflare_dns_record" "photos_staging" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "photos"
  content = aws_cloudfront_distribution.photos["staging"].domain_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Photo CDN (CloudFront) behind CloudFlare cache - managed by Terraform"
}

# Status page hosted by Checkly - must be unproxied (grey cloud) so Checkly can
# validate the domain and issue its own certificate.
resource "cloudflare_dns_record" "status" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "status"
  content = "checkly-dashboards.com"
  type    = "CNAME"
  proxied = false # Checkly terminates TLS itself
  ttl     = 600   # 10 minutes

  comment = "Checkly status dashboard for TrigpointingUK - managed by Terraform"
}

# Root domain (apex) - staging
# Note: At apex, use CNAME with proxied=true and CloudFlare will flatten it
# If IPv4 issues persist, the ALB may need dualstack configuration
resource "cloudflare_dns_record" "root_domain_staging" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "@" # Root domain
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Root domain pointing to ALB for staging - managed by Terraform"
}

# Root domain (apex) - production
resource "cloudflare_dns_record" "root_domain_production" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "@" # Root domain
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Root domain pointing to ALB via nginx proxy - managed by Terraform"
}

# WWW subdomain - staging
resource "cloudflare_dns_record" "www_staging" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "www"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "WWW subdomain pointing to ALB for staging - managed by Terraform"
}

# WWW subdomain - production
resource "cloudflare_dns_record" "www_production" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "www"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "WWW subdomain pointing to ALB via nginx proxy - managed by Terraform"
}

# Redirect wiki URLs on apex to wiki subdomain
## Bulk Redirects for wiki paths (account-level)
# List holding the redirects
resource "cloudflare_list" "wiki_redirects" {
  account_id  = var.cloudflare_account_id
  name        = "wiki_redirects"
  description = "Redirect /w/* and /wiki* on trigpointing.uk to wiki.trigpointing.uk"
  kind        = "redirect"
}

# Redirect: https://trigpointing.uk/w -> https://wiki.trigpointing.uk (drop /w, preserve subpath + query)
resource "cloudflare_list_item" "wiki_redirect_w" {
  account_id = var.cloudflare_account_id
  list_id    = cloudflare_list.wiki_redirects.id

  redirect = {
    source_url            = "https://trigpointing.uk/w"
    target_url            = "https://wiki.trigpointing.uk"
    status_code           = 301
    include_subdomains    = true
    subpath_matching      = true
    preserve_query_string = true
    preserve_path_suffix  = false
  }
}

# Redirect: https://trigpointing.uk/wiki -> https://wiki.trigpointing.uk (drop /wiki, preserve subpath + query)
resource "cloudflare_list_item" "wiki_redirect_wiki" {
  account_id = var.cloudflare_account_id
  list_id    = cloudflare_list.wiki_redirects.id

  redirect = {
    source_url            = "https://trigpointing.uk/wiki"
    target_url            = "https://wiki.trigpointing.uk"
    status_code           = 301
    include_subdomains    = true
    subpath_matching      = true
    preserve_query_string = true
    preserve_path_suffix  = false
  }
}

# Activate the list via an account-level redirect ruleset
## Activation of the list is done via Cloudflare Dashboard (existing account Redirect ruleset)

# Bulk Redirects for forum path (account-level)
# Redirect: https://trigpointing.uk/forum/* -> https://forum.trigpointing.uk/* (preserve subpath + query)
resource "cloudflare_list" "forum_redirects" {
  account_id  = var.cloudflare_account_id
  name        = "forum_redirects"
  description = "Redirect /forum/* on trigpointing.uk to forum.trigpointing.uk"
  kind        = "redirect"
}

resource "cloudflare_list_item" "forum_redirect_forum" {
  account_id = var.cloudflare_account_id
  list_id    = cloudflare_list.forum_redirects.id

  redirect = {
    source_url            = "https://trigpointing.uk/forum"
    target_url            = "https://forum.trigpointing.uk"
    status_code           = 301
    include_subdomains    = true
    subpath_matching      = true
    preserve_query_string = true
    preserve_path_suffix  = false
  }
}

# Activation of the list is handled by the existing account-level Redirect ruleset in Cloudflare

# Bulk Redirects: www → apex (canonical non-www domain)
# Ensures a single origin for CORS, Auth0 callbacks, and SEO.
resource "cloudflare_list" "www_redirects" {
  account_id  = var.cloudflare_account_id
  name        = "www_redirects"
  description = "Redirect www.trigpointing.uk and www.trigpointing.me to their apex domains"
  kind        = "redirect"
}

resource "cloudflare_list_item" "www_redirect_production" {
  account_id = var.cloudflare_account_id
  list_id    = cloudflare_list.www_redirects.id

  redirect = {
    source_url            = "https://www.trigpointing.uk/"
    target_url            = "https://trigpointing.uk/"
    status_code           = 301
    include_subdomains    = false
    subpath_matching      = true
    preserve_query_string = true
    preserve_path_suffix  = true
  }
}

resource "cloudflare_list_item" "www_redirect_staging" {
  account_id = var.cloudflare_account_id
  list_id    = cloudflare_list.www_redirects.id

  redirect = {
    source_url            = "https://www.trigpointing.me/"
    target_url            = "https://trigpointing.me/"
    status_code           = 301
    include_subdomains    = false
    subpath_matching      = true
    preserve_query_string = true
    preserve_path_suffix  = true
  }
}
