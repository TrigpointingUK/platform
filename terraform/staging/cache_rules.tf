# Cloudflare Cache Rules for Staging Environment
# These rules control caching behavior for trigpointing.me and www.trigpointing.me
#
# NOTE: This manages the existing "default" cache ruleset for the zone.
# To import: terraform import cloudflare_ruleset.cache_rules 98029aec0625eb04469b262a68b2c676/ee042a4924034c64b442027f62fa4f4a

resource "cloudflare_ruleset" "cache_rules" {
  zone_id     = data.cloudflare_zones.staging.result[0].id
  name        = "default"
  description = ""
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules = [
    # Rule 1: Bypass cache for SPA routes (all non-asset paths)
    # Priority: Highest - ensure HTML/SPA routes are never cached
    # This covers all client-side routes like /trigs, /logs, /users, etc.
    {
      action      = "set_cache_settings"
      expression  = "(http.host in {\"trigpointing.me\" \"www.trigpointing.me\"}) and not starts_with(http.request.uri.path, \"/assets/\") and not starts_with(http.request.uri.path, \"/v1/\")"
      description = "Bypass cache for SPA routes (all non-asset paths)"
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
      expression  = "http.host in {\"trigpointing.me\" \"www.trigpointing.me\"}"
      description = "Respect origin cache headers for all other resources"
      enabled     = true

      action_parameters = {
        cache                = true
        respect_strong_etags = true
        # This makes assets eligible for cache while respecting origin headers
        # Static assets with Cache-Control: immutable will be cached
        # API responses with no-cache will not be cached
      }
    },

    # Rule 4: Photo bucket - cache aggressively.
    # S3 sends no Cache-Control header, so without an explicit edge_ttl override
    # CloudFlare would fall back to a short default TTL and most views would still
    # reach S3 as billable egress. Photo object names carry a revision suffix
    # (P451921_r1.jpg), so a new upload or rotation produces a new key and the
    # cached copy never goes stale.
    # No other rule in this ruleset matches the photos.* host, so this rule is
    # order-independent and is appended to keep the diff on existing rules empty.
    {
      action      = "set_cache_settings"
      expression  = "(http.host eq \"photos.trigpointing.me\")"
      description = "Cache photo bucket objects at the edge"
      enabled     = true

      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = 2592000 # 30 days
        }
        browser_ttl = {
          mode    = "override_origin"
          default = 604800 # 7 days
        }
        respect_strong_etags = true
        serve_stale = {
          disable_stale_while_updating = false
        }
      }
    }
  ]
}

