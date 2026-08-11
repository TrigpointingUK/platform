# This module creates both the HTTPS listener and certificate for the first environment (staging)

# CloudFlare Origin Certificate
resource "aws_acm_certificate" "cloudflare_origin" {
  count            = var.enable_cloudflare_ssl ? 1 : 0
  certificate_body = var.cloudflare_origin_cert
  private_key      = var.cloudflare_origin_key

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-cloudflare-cert"
    Type        = "CloudFlare Origin Certificate"
    Environment = var.environment
    Domain      = var.domain_name
  }
}

# HTTPS Listener with CloudFlare Origin Certificate
# This creates the shared listener that all environments will use
resource "aws_lb_listener" "app_https" {
  count             = var.enable_cloudflare_ssl ? 1 : 0
  load_balancer_arn = var.alb_arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09"
  certificate_arn   = aws_acm_certificate.cloudflare_origin[0].arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "No matching host configured"
      status_code  = "404"
    }
  }

  tags = {
    Name      = "${var.project_name}-shared-https-listener"
    CreatedBy = var.environment
  }
}
