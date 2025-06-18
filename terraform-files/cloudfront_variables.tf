variable "cloudfront_distribution_name" {
  type = map(string)
  default = {
    "dev"  = "dev-cms-cloudfront"
    "test" = "test-cms-cloudfront"
    "prod" = "prod-cms-cloudfront"
  }
}

variable "cloudfront_domain_name" {
  type = map(string)
  default = {
    "dev"  = "devapi.turtilcms.turtil.co"
    "test" = "testapi.turtilcms.turtil.co"
    "prod" = "api.turtilcms.turtil.co" # e.g., "app.example.com"
  }
}

variable "cloudfront_route53_zone_id" {
  type = map(string)
  default = {
    "dev"  = "Z0964890C8UWZEUGAVHY"
    "test" = "Z0964890C8UWZEUGAVHY"
    "prod" = "Z0964890C8UWZEUGAVHY" # e.g., "Z1234567890"
  }
}

variable "cloudfront_acm_certificate_arn" {
  type = map(string)
  default = {
    "dev"  = "arn:aws:acm:us-east-1:033464272864:certificate/18c4d54b-81f8-45af-b192-72fe1bba226b"
    "test" = null
    "prod" = null
  }
}