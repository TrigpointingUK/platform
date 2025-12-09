# Cloudflare Cache Rules for Production Environment
# These rules control caching behavior for trigpointing.uk and www.trigpointing.uk
#
# NOTE: This manages the existing "default" cache ruleset for the zone.
# Imported with: terraform import cloudflare_ruleset.cache_rules zones/5a8a43d37aff74c0504bb729ed4f379e/b36366930c0045a8aa24b79b35d26cf6

resource "cloudflare_ruleset" "cache_rules" {
  zone_id     = data.cloudflare_zones.production.result[0].id
  name        = "default"
  description = ""
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules = [
    # Rule 1: Bypass cache for SPA routes (all non-asset paths under /app/)
    # Priority: Highest - ensure HTML/SPA routes are never cached
    # This covers all client-side routes like /app/trigs, /app/logs, /app/users, etc.
    {
      action      = "set_cache_settings"
      expression  = "(http.host in {\"trigpointing.uk\" \"www.trigpointing.uk\"}) and starts_with(http.request.uri.path, \"/app/\") and not starts_with(http.request.uri.path, \"/app/assets/\")"
      description = "Bypass cache for SPA routes (all non-asset paths under /app/)"
      enabled     = true

      action_parameters = {
        cache = false # Bypass cache entirely for SPA routes
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

