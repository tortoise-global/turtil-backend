output "certificate_arn" {
  description = "The ARN of the validated certificate"
  value       = aws_acm_certificate.this.arn
}

output "certificate_domain" {
  description = "Domain of the issued certificate"
  value       = aws_acm_certificate.this.domain_name
}

output "validation_fqdns" {
  description = "The FQDNs used for DNS validation"
  value       = [for r in aws_route53_record.validation : r.fqdn]
}
