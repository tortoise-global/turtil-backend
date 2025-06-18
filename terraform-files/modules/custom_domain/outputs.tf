output "custom_domain__api" {
  value = "https://${aws_apigatewayv2_api_mapping.api.domain_name}"
}

output "custom_domain_api__v1" {
  value = "https://${aws_apigatewayv2_api_mapping.api_v1.domain_name}/${aws_apigatewayv2_api_mapping.api_v1.api_mapping_key}"
}