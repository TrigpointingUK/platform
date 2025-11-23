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

    # Rule 2: API Export endpoints - short cache with revalidation
    # Combines /v1/trigs/export and /v1/trigs/geojson to save on rule limit
    {
      action      = "set_cache_settings"
      expression  = "(http.request.uri.path wildcard r\"/v1/trigs/export\") or (http.request.uri.path wildcard r\"/v1/trigs/geojson\")"
      description = "API Export endpoints - short cache, revalidates via ETag"
      enabled     = true

      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = 300 # 5 minutes (API handles freshness with 60s checks)
        }
        browser_ttl = {
          mode = "respect_origin" # Respect the Cache-Control: max-age=60
        }
        serve_stale = {
          disable_stale_while_updating = false
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

