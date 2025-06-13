variable "distribution_name" {
  description = "Name of the CloudFront distribution"
  type        = string
}

variable "alb_dns_name" {
  description = "DNS name of the ALB to use as origin (optional, null for non-ALB origin)"
  type        = string
  default     = null
}

variable "domain_name" {
  description = "Domain name for the CloudFront distribution (optional)"
  type        = string
  default     = null
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID for domain mapping (optional)"
  type        = string
  default     = null
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate in us-east-1 for SSL (optional)"
  type        = string
  default     = null
}

variable "default_root_object" {
  description = "Default root object for the distribution"
  type        = string
  default     = "index.html"
}

variable "price_class" {
  description = "CloudFront price class (PriceClass_All, PriceClass_200, PriceClass_100)"
  type        = string
  default     = "PriceClass_100"
}

variable "cache_ttl" {
  description = "Cache TTL settings for default cache behavior"
  type = object({
    min     = number
    default = number
    max     = number
  })
  default = {
    min     = 0
    default = 86400
    max     = 31536000
  }
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default     = {}
}