# Cloudflare Cache Rules for Production Environment
# These rules control caching behavior for trigpointing.uk and www.trigpointing.uk

resource "cloudflare_ruleset" "cache_rules" {
  zone_id     = data.cloudflare_zones.production.result[0].id
  name        = "Production Cache Rules"
  description = "Cache rules for production: bypass HTML, long cache for static assets and API exports"
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules = [
    # Rule 1: Bypass cache for HTML files (SPA entrypoints)
    # Priority: Highest - ensure HTML is never cached
    {
      action      = "set_cache_settings"
      expression  = "(http.host in {\"trigpointing.uk\" \"www.trigpointing.uk\"}) and (http.request.uri.path eq \"/\" or http.request.uri.path eq \"/index.html\" or http.request.uri.path eq \"/app/\" or http.request.uri.path eq \"/app/index.html\")"
      description = "Bypass cache for HTML files"
      enabled     = true

      action_parameters = {
        cache = false # Bypass cache entirely for HTML
      }
    },

    # Rule 2: Long cache for Android export file
    # This file is generated infrequently and can be cached for a long time
    {
      action      = "set_cache_settings"
      expression  = "(http.host in {\"api.trigpointing.uk\"}) and (http.request.uri.path eq \"/android-export\")"
      description = "Android Export File - long cache"
      enabled     = true

      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = 86400 # 24 hours
        }
        browser_ttl = {
          mode    = "override_origin"
          default = 3600 # 1 hour
        }
      }
    },

    # Rule 3: Respect origin cache headers for all other requests
    # This allows static assets with Cache-Control: immutable to be cached
    # while respecting no-cache headers from dynamic content
    {
      action      = "set_cache_settings"
      expression  = "http.host in {\"trigpointing.uk\" \"www.trigpointing.uk\"}"
      description = "Respect origin cache headers for all other resources"
      enabled     = true

      action_parameters = {
        cache                = true
        respect_strong_etags = true
        # This makes assets eligible for cache while respecting origin headers
        # Static assets with Cache-Control: immutable will be cached
        # API responses with no-cache will not be cached
      }
    }
  ]
}

