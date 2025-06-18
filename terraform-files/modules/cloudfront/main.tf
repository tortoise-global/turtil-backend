# Create CloudFront distribution
resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = var.default_root_object
  price_class         = var.price_class

  # Origin configuration
  dynamic "origin" {
    for_each = var.alb_dns_name != null ? [1] : []
    content {
      domain_name = var.alb_dns_name
      origin_id   = "${var.distribution_name}-alb-origin"

      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "http-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  # Fallback origin (e.g., S3) if ALB is not used
  dynamic "origin" {
    for_each = var.alb_dns_name == null ? [1] : []
    content {
      domain_name = "example-bucket.s3.amazonaws.com"
      origin_id   = "${var.distribution_name}-s3-origin"

      s3_origin_config {
        origin_access_identity = ""
      }
    }
  }

  # Default cache behavior
  default_cache_behavior {
    target_origin_id       = var.alb_dns_name != null ? "${var.distribution_name}-alb-origin" : "${var.distribution_name}-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    min_ttl                = var.cache_ttl.min
    default_ttl            = var.cache_ttl.default
    max_ttl                = var.cache_ttl.max
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }
  }

  # Viewer certificate (ACM or default CloudFront)
  viewer_certificate {
    acm_certificate_arn            = var.acm_certificate_arn
    ssl_support_method             = var.acm_certificate_arn != null ? "sni-only" : null
    minimum_protocol_version       = "TLSv1.2_2021"
    cloudfront_default_certificate = var.acm_certificate_arn == null ? true : null
  }

  # Domain aliases (if domain_name is provided)
  aliases = var.domain_name != null ? [var.domain_name] : []

  # Restrictions
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Custom error responses
  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/error.html"
  }

  # Tags
  tags = merge(var.tags, {
    Name = var.distribution_name
  })
}

# Route 53 record (if domain_name and route53_zone_id are provided)
resource "aws_route53_record" "this" {
  count   = var.domain_name != null && var.route53_zone_id != null ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}