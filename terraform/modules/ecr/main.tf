# ============================================================================
# ECR REPOSITORY MODULE
# ============================================================================
# Enhanced ECR module with environment-specific features

# ECR Repository
resource "aws_ecr_repository" "this" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  # Encryption configuration
  encryption_configuration {
    encryption_type = var.encryption_type
    kms_key        = var.kms_key_id != "" ? var.kms_key_id : null
  }

  tags = merge(var.tags, {
    Name = var.repository_name
    Type = "container-registry"
  })
}

# Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "this" {
  count      = var.enable_lifecycle_policy ? 1 : 0
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last ${var.max_image_count} tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = var.keep_image_tag_prefixes
          countType     = "imageCountMoreThan"
          countNumber   = var.max_image_count
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep untagged images for ${var.untagged_image_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_image_days
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Repository Policy for cross-account access (if specified)
resource "aws_ecr_repository_policy" "this" {
  count      = var.repository_policy != "" ? 1 : 0
  repository = aws_ecr_repository.this.name
  policy     = var.repository_policy
}

# Enhanced Image Scanning (if enabled)
resource "aws_ecr_registry_scanning_configuration" "this" {
  count = var.enable_enhanced_scanning ? 1 : 0

  scan_type = "ENHANCED"

  rule {
    scan_frequency = var.enhanced_scan_frequency
    repository_filter {
      filter      = aws_ecr_repository.this.name
      filter_type = "WILDCARD"
    }
  }
}

# Repository replication (for cross-region disaster recovery)
resource "aws_ecr_replication_configuration" "this" {
  count = var.enable_cross_region_replication ? 1 : 0

  replication_configuration {
    rule {
      destination {
        region      = var.replication_destination_region
        registry_id = var.replication_destination_registry_id
      }

      repository_filter {
        filter      = aws_ecr_repository.this.name
        filter_type = "PREFIX_MATCH"
      }
    }
  }
}