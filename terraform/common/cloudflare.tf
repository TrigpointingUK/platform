# CloudFlare DNS Records
# Creates CNAME records for both staging and production domains

# Data source to get zone information
data "cloudflare_zones" "staging" {
  name = "trigpointing.me"
}

data "cloudflare_zones" "production" {
  name = "trigpointing.uk"
}

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

resource "cloudflare_dns_record" "static" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "static"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true # Enable CloudFlare proxy (orange cloud)
  ttl     = 1    # Auto TTL when proxied

  comment = "Static content subdomain for TrigpointingUK - managed by Terraform"
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
  }
}

# Activation of the list is handled by the existing account-level Redirect ruleset in Cloudflare
