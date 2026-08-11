# Photo delivery CDN
#
# Request path: browser -> CloudFlare (proxied) -> CloudFront -> S3
#
# Why CloudFront is in the path at all: CloudFlare would otherwise have to talk to
# S3 directly, and S3 resolves the bucket from the Host header. Rewriting that
# header needs CloudFlare's Host Header Override, which is a Pro+ entitlement and
# our zones are on Free ("not entitled to use the HostHeader override"). CloudFront
# sets the origin Host itself, so it sidesteps the problem.
#
# It is also cheaper than fronting S3 directly: data transfer from S3 to CloudFront
# is free, and CloudFront's perpetual free tier (1 TB egress, 10M requests/month)
# is roughly 3x current photo traffic. CloudFlare absorbs most requests before
# CloudFront ever sees them.
#
# The buckets remain publicly readable, so existing direct S3 URLs embedded in
# forum posts, wiki pages and third-party sites keep working. That means the CDN
# can still be bypassed; the S3 access logs enabled in s3-access-logs.tf will show
# how much traffic does so, and locking the buckets to CloudFront-only via an
# origin access control is a follow-up decision to take on that evidence.

locals {
  photos_cdn = {
    production = {
      zone_id     = data.cloudflare_zones.production.result[0].id
      hostname    = "photos.trigpointing.uk"
      bucket      = "trigpointinguk-photos"
      description = "TrigpointingUK production photos"
    }
    staging = {
      zone_id     = data.cloudflare_zones.staging.result[0].id
      hostname    = "photos.trigpointing.me"
      bucket      = "trigpointinguk-test"
      description = "TrigpointingUK staging photos"
    }
  }
}

# CloudFront matches a distribution by the Host header CloudFlare forwards, so each
# hostname must be an alias backed by a certificate covering it.
resource "aws_acm_certificate" "photos" {
  for_each = local.photos_cdn
  provider = aws.us_east_1

  domain_name       = each.value.hostname
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# Validation records must be unproxied - CloudFlare's proxy would mask the CNAME
# and ACM would never see it.
resource "cloudflare_dns_record" "photos_cert_validation" {
  for_each = {
    for k, v in local.photos_cdn : k => {
      zone_id = v.zone_id
      option  = tolist(aws_acm_certificate.photos[k].domain_validation_options)[0]
    }
  }

  zone_id = each.value.zone_id
  name    = trimsuffix(each.value.option.resource_record_name, ".")
  content = trimsuffix(each.value.option.resource_record_value, ".")
  type    = each.value.option.resource_record_type
  proxied = false
  ttl     = 60

  comment = "ACM DNS validation for photo CDN - managed by Terraform"
}

resource "aws_acm_certificate_validation" "photos" {
  for_each = local.photos_cdn
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.photos[each.key].arn
  validation_record_fqdns = [cloudflare_dns_record.photos_cert_validation[each.key].name]
}

resource "aws_cloudfront_distribution" "photos" {
  for_each = local.photos_cdn

  enabled         = true
  comment         = each.value.description
  aliases         = [each.value.hostname]
  price_class     = "PriceClass_100" # NA + Europe; the audience is overwhelmingly UK
  is_ipv6_enabled = true
  http_version    = "http2and3"

  origin {
    origin_id   = each.value.bucket
    domain_name = "${each.value.bucket}.s3.${var.aws_region}.amazonaws.com"

    # The buckets are publicly readable, so no origin access control is attached.
    # CloudFront reaches them over the public S3 REST endpoint. Switch this to an
    # aws_cloudfront_origin_access_control if the buckets are ever locked down.
    custom_origin_config {
      origin_protocol_policy = "https-only"
      http_port              = 80
      https_port             = 443
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = each.value.bucket
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # AWS managed "CachingOptimized" policy: long TTLs, no cookies or query strings
    # in the cache key. Photo keys carry a revision suffix (P451921_r1.jpg), so a
    # replacement upload produces a new key and cached copies never go stale.
    cache_policy_id = data.aws_cloudfront_cache_policy.caching_optimized.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.photos[each.key].certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}
