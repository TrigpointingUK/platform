# S3 server access logging
#
# Enables request-level logging on the public-facing buckets so we can attribute
# egress to a requester (remote IP, user-agent, referer, bytes sent, object key).
# Neither CloudTrail (management events only) nor Cost Explorer can do this.
#
# Cost note: log delivery PUTs are not billed; only log storage is. At current
# request rates (~85k/day) this is roughly 1 GB/month, so a few pence. The real
# hazard is unbounded accumulation of tiny objects - the trigpointinguk-retriangulation
# bucket has 8.9M log objects dating back to 2013 because nothing ever expired them.
# The lifecycle rule below is the guard; tune it with s3_access_log_retention_days.

resource "aws_s3_bucket" "access_logs" {
  bucket        = "trigpointinguk-s3-access-logs"
  force_destroy = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    apply_server_side_encryption_by_default {
      # Log delivery supports SSE-S3 without extra configuration. Do not switch
      # to SSE-KMS without also granting the log delivery service kms:GenerateDataKey.
      sse_algorithm = "AES256"
    }
  }
}

# Logs are internal only - no ACLs, no public access.
resource "aws_s3_bucket_ownership_controls" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket                  = aws_s3_bucket.access_logs.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# Expire logs on a single knob. Access logs are written as many small objects,
# so the transition to a cheaper class is deliberately omitted - per-object
# transition charges would cost more than the storage they save.
resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "expire-access-logs"
    status = "Enabled"

    filter {}

    expiration {
      days = var.s3_access_log_retention_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Allow the S3 log delivery service to write logs for our source buckets only.
resource "aws_s3_bucket_policy" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3ServerAccessLogDelivery"
        Effect = "Allow"
        Principal = {
          Service = "logging.s3.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.access_logs.arn}/*"
        Condition = {
          ArnLike = {
            "aws:SourceArn" = [for b in local.access_log_sources : "arn:aws:s3:::${b}"]
          }
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.access_logs.arn,
          "${aws_s3_bucket.access_logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Source buckets to log, keyed by the log prefix they write under.
# trigpointinguk-photos (production) and trigpointinguk-test (staging) are the
# photo buckets; maps holds the multi-GB offline map packs; opengraph and avatars
# are both served as direct public S3 URLs.
locals {
  access_log_sources = [
    "trigpointinguk-photos",
    "trigpointinguk-test",
    "trigpointinguk-maps",
    "trigpointinguk-opengraph",
    "trigpointinguk-avatars",
  ]
}

# These buckets predate Terraform and are intentionally not managed here - only
# their logging configuration is. Referencing by name avoids importing them.
resource "aws_s3_bucket_logging" "sources" {
  for_each = toset(local.access_log_sources)

  bucket        = each.value
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "${each.value}/"

  depends_on = [aws_s3_bucket_policy.access_logs]
}
