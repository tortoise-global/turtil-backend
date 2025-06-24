# ============================================================================
# S3 BUCKET MODULE - MULTI-ENVIRONMENT SUPPORT
# ============================================================================
# Enhanced S3 module with lifecycle policies, versioning, and CORS

locals {
  bucket_name = var.bucket_name
  is_production = var.environment == "prod"
}

# Main S3 Bucket
resource "aws_s3_bucket" "main" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy

  tags = merge(var.tags, {
    Name = local.bucket_name
    Environment = var.environment
    Purpose = var.bucket_purpose
  })
}

# Bucket Versioning
resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

# Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != "" ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id != "" ? var.kms_key_id : null
    }
    bucket_key_enabled = var.kms_key_id != "" ? true : false
  }
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = var.block_public_access
  block_public_policy     = var.block_public_access
  ignore_public_acls      = var.block_public_access
  restrict_public_buckets = var.block_public_access
}

# CORS Configuration for direct uploads
resource "aws_s3_bucket_cors_configuration" "main" {
  count = var.enable_cors ? 1 : 0
  
  bucket = aws_s3_bucket.main.id

  cors_rule {
    allowed_headers = var.cors_allowed_headers
    allowed_methods = var.cors_allowed_methods
    allowed_origins = var.cors_allowed_origins
    expose_headers  = var.cors_expose_headers
    max_age_seconds = var.cors_max_age_seconds
  }
}

# Lifecycle Policy
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  count = var.enable_lifecycle ? 1 : 0
  
  bucket = aws_s3_bucket.main.id

  # Standard to Infrequent Access transition
  dynamic "rule" {
    for_each = var.transition_to_ia_days > 0 ? [1] : []
    
    content {
      id     = "transition-to-ia"
      status = "Enabled"

      transition {
        days          = var.transition_to_ia_days
        storage_class = "STANDARD_IA"
      }

      noncurrent_version_transition {
        noncurrent_days = var.transition_to_ia_days
        storage_class   = "STANDARD_IA"
      }
    }
  }

  # Glacier transition
  dynamic "rule" {
    for_each = var.transition_to_glacier_days > 0 ? [1] : []
    
    content {
      id     = "transition-to-glacier"
      status = "Enabled"

      transition {
        days          = var.transition_to_glacier_days
        storage_class = "GLACIER"
      }

      noncurrent_version_transition {
        noncurrent_days = var.transition_to_glacier_days
        storage_class   = "GLACIER"
      }
    }
  }

  # Deep Archive transition
  dynamic "rule" {
    for_each = var.transition_to_deep_archive_days > 0 ? [1] : []
    
    content {
      id     = "transition-to-deep-archive"
      status = "Enabled"

      transition {
        days          = var.transition_to_deep_archive_days
        storage_class = "DEEP_ARCHIVE"
      }

      noncurrent_version_transition {
        noncurrent_days = var.transition_to_deep_archive_days
        storage_class   = "DEEP_ARCHIVE"
      }
    }
  }

  # Object expiration
  dynamic "rule" {
    for_each = var.expiration_days > 0 ? [1] : []
    
    content {
      id     = "object-expiration"
      status = "Enabled"

      expiration {
        days = var.expiration_days
      }

      noncurrent_version_expiration {
        noncurrent_days = var.expiration_days
      }
    }
  }

  # Incomplete multipart upload cleanup
  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Intelligent Tiering (Production only)
resource "aws_s3_bucket_intelligent_tiering_configuration" "main" {
  count = var.enable_intelligent_tiering ? 1 : 0
  
  bucket = aws_s3_bucket.main.id
  name   = "entire-bucket"
  status = "Enabled"

  # Archive configurations
  dynamic "tiering" {
    for_each = var.intelligent_tiering_archive_days > 0 ? [1] : []
    
    content {
      access_tier = "ARCHIVE_ACCESS"
      days        = var.intelligent_tiering_archive_days
    }
  }

  dynamic "tiering" {
    for_each = var.intelligent_tiering_deep_archive_days > 0 ? [1] : []
    
    content {
      access_tier = "DEEP_ARCHIVE_ACCESS"
      days        = var.intelligent_tiering_deep_archive_days
    }
  }
}

# Bucket Notification for monitoring
resource "aws_s3_bucket_notification" "main" {
  count = var.enable_notifications ? 1 : 0
  
  bucket = aws_s3_bucket.main.id

  # CloudWatch Events for monitoring
  eventbridge = var.enable_eventbridge_notifications
}

# Cross-Region Replication (Production only)
resource "aws_s3_bucket_replication_configuration" "main" {
  count = var.enable_cross_region_replication ? 1 : 0
  
  role   = aws_iam_role.replication[0].arn
  bucket = aws_s3_bucket.main.id

  depends_on = [aws_s3_bucket_versioning.main]

  rule {
    id     = "replicate-everything"
    status = "Enabled"

    destination {
      bucket        = var.replication_destination_bucket
      storage_class = var.replication_storage_class

      dynamic "encryption_configuration" {
        for_each = var.replication_kms_key_id != "" ? [1] : []
        
        content {
          replica_kms_key_id = var.replication_kms_key_id
        }
      }
    }
  }
}

# IAM Role for Cross-Region Replication
resource "aws_iam_role" "replication" {
  count = var.enable_cross_region_replication ? 1 : 0
  
  name = "${local.bucket_name}-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "replication" {
  count = var.enable_cross_region_replication ? 1 : 0
  
  name = "${local.bucket_name}-replication-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Resource = "${aws_s3_bucket.main.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Resource = "${var.replication_destination_bucket}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "replication" {
  count = var.enable_cross_region_replication ? 1 : 0
  
  role       = aws_iam_role.replication[0].name
  policy_arn = aws_iam_policy.replication[0].arn
}
