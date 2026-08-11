# Single HTTPS Listener for all environments (supports multiple certificates via SNI)
# This listener is created with a self-signed certificate initially,
# then environments add their own certificates
resource "tls_private_key" "default" {
  count     = var.enable_cloudflare_ssl ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "default" {
  count           = var.enable_cloudflare_ssl ? 1 : 0
  private_key_pem = tls_private_key.default[0].private_key_pem

  subject {
    common_name  = "default.local"
    organization = "Default"
  }

  validity_period_hours = 87600 # 10 years

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

resource "aws_acm_certificate" "default" {
  count            = var.enable_cloudflare_ssl ? 1 : 0
  certificate_body = tls_self_signed_cert.default[0].cert_pem
  private_key      = tls_private_key.default[0].private_key_pem

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_name}-default-cert"
    Type = "Default Self-Signed Certificate"
  }
}

resource "aws_lb_listener" "app_https" {
  count             = var.enable_cloudflare_ssl ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09"
  certificate_arn   = aws_acm_certificate.default[0].arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "No matching host configured"
      status_code  = "404"
    }
  }

  tags = {
    Name = "${var.project_name}-https-listener"
  }
}
