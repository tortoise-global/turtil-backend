variable "domain_name" {
  description = "Primary domain for the ACM certificate"
  type        = string
}

variable "subject_alternative_names" {
  description = "SANs (alternate domain names)"
  type        = list(string)
  default     = []
}

variable "hosted_zone_id" {
  description = "Route53 Hosted Zone ID"
  type        = string
}

variable "tags" {
  description = "Tags to assign"
  type        = map(string)
  default     = {}
}
