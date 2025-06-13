# resource "aws_apigatewayv2_integration" "integrations" {
#   for_each = { for integration in var.integrations : integration.name => integration }
#   api_id             = var.api_id
#   integration_uri    = each.value.uri
#   integration_type   = "AWS_PROXY"
#   integration_method = "POST"
# }

resource "aws_apigatewayv2_integration" "integrations" {
  for_each               = { for integration in var.integrations : integration.name => integration }
  api_id                 = var.api_id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value.uri
  integration_method     = "POST"
  payload_format_version = "1.0"
}