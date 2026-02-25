# S3 bucket for user avatar images (publicly readable)

resource "aws_s3_bucket" "avatars" {
  bucket        = "trigpointinguk-avatars"
  force_destroy = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "avatars" {
  bucket = aws_s3_bucket.avatars.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Allow object-level ACLs so the API can set ACL="public-read" on put_object
resource "aws_s3_bucket_ownership_controls" "avatars" {
  bucket = aws_s3_bucket.avatars.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Permit public ACLs - objects are served directly via S3 public URLs
resource "aws_s3_bucket_public_access_block" "avatars" {
  bucket                  = aws_s3_bucket.avatars.id
  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = true
  restrict_public_buckets = true
}
