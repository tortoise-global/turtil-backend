
# ACM Certificate Module Usage
module "acm_certificate" {
  source = "./modules/acm"

  domain_name                = var.acm_domain_names[terraform.workspace]
  subject_alternative_names = var.acm_san_names[terraform.workspace]
  hosted_zone_id            = var.acm_hosted_zone_ids[terraform.workspace]

  tags = {
    Environment = var.acm_env_tags[terraform.workspace]
    Project     = "turtil cms"
  }
}
output "certificate_manager_arn" {
  description = "Exported ACM certificate ARN from module"
  value       = module.acm_certificate.certificate_arn
}