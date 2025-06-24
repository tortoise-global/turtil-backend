resource "aws_acm_certificate" "api" {
  domain_name       = lookup(var.domain_name, terraform.workspace)
  validation_method = lookup(var.validation_method, terraform.workspace)
}

data "aws_route53_zone" "public" {
  name         = lookup(var.route53_zone_name, terraform.workspace)
  private_zone = false
}

resource "aws_route53_record" "api_validation" {
  for_each        = { for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => dvo }
  allow_overwrite = true
  name            = each.value.resource_record_name
  records         = [each.value.resource_record_value]
  ttl             = lookup(var.route53_ttl, terraform.workspace)
  type            = each.value.resource_record_type
  zone_id         = data.aws_route53_zone.public.zone_id
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for record in aws_route53_record.api_validation : record.fqdn]
}

resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = lookup(var.domain_name, terraform.workspace)
  domain_name_configuration {
    certificate_arn = aws_acm_certificate.api.arn
    endpoint_type   = lookup(var.endpoint_type, terraform.workspace)
    security_policy = lookup(var.security_policy, terraform.workspace)
  }
  depends_on = [aws_acm_certificate_validation.api]
}

resource "aws_route53_record" "api" {
  name    = aws_apigatewayv2_domain_name.api.domain_name
  type    = "A"
  zone_id = data.aws_route53_zone.public.zone_id
  alias {
    name                   = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = var.api_id
  domain_name = aws_apigatewayv2_domain_name.api.id
  stage       = var.stage_id
}


resource "aws_apigatewayv2_api_mapping" "api_v1" {
  api_id          = var.api_id
  domain_name     = aws_apigatewayv2_domain_name.api.id
  stage           = var.stage_id
  api_mapping_key = lookup(var.api_mapping_key, terraform.workspace)
}

# Second API Gateway Base Path Mapping
resource "aws_apigatewayv2_api_mapping" "api_v2" {
  api_id          = var.api_id_2 # ID of the second API Gateway
  domain_name     = aws_apigatewayv2_domain_name.api.id
  stage           = var.stage_id_2
  api_mapping_key = lookup(var.api_mapping_key_2, terraform.workspace) # Base path for the second API
}

# Third API Gateway Base Path Mapping
resource "aws_apigatewayv2_api_mapping" "api_v3" {
  api_id          = var.api_id_3 # ID of the third API Gateway
  domain_name     = aws_apigatewayv2_domain_name.api.id
  stage           = var.stage_id_3
  api_mapping_key = lookup(var.api_mapping_key_3, terraform.workspace) # Base path for the third API
}


output "custom_domain_api" {
  value = "https://${aws_apigatewayv2_api_mapping.api.domain_name}"
}

output "custom_domain_api_v1" {
  value = "https://${aws_apigatewayv2_api_mapping.api_v1.domain_name}/${aws_apigatewayv2_api_mapping.api_v1.api_mapping_key}"
}

output "custom_domain_api_v3" {
  value = "https://${aws_apigatewayv2_api_mapping.api_v2.domain_name}/${aws_apigatewayv2_api_mapping.api_v2.api_mapping_key}"
}
