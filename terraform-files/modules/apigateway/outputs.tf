output "stage_name" {
  value = aws_apigatewayv2_stage.this.name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.api_gw.name
}

output "integration_ids" {
  value = { for name, integ in aws_apigatewayv2_integration.integrations : name => integ.id }
}

output "route_keys" {
  value = { for key, route in aws_apigatewayv2_route.routes : key => route.route_key }
}

output "authorizer_id" {
  value = aws_apigatewayv2_authorizer.cognito_authorizer.id
}

output "api_gateway_url" {
  value = aws_apigatewayv2_stage.this.invoke_url
}

output "stage_id" {
  value = aws_apigatewayv2_stage.this.id
}


