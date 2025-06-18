resource "aws_apigatewayv2_route" "routes" {
  for_each = { for route in var.routes : route.route_key => route }

  api_id             = var.api_id
  route_key          = each.value.route_key
  target             = "integrations/${aws_apigatewayv2_integration.integrations[each.value.integration_name].id}"
  authorizer_id      = each.value.authorize ? aws_apigatewayv2_authorizer.cognito_authorizer.id : null
  authorization_type = each.value.authorize ? "JWT" : "NONE" #imp
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/api-gw/${var.api_id}"
  retention_in_days = var.log_retention_days
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = var.api_id
  name        = var.stage_name
  auto_deploy = true

  # Throttling settings applied to all routes

  default_route_settings {
    throttling_burst_limit = 4000
    throttling_rate_limit  = 8000
  }

  # Route-specific throttling settings
  # dynamic "route_settings" {
  #   for_each = { for route in var.routes : route.route_key => route }

  #   content {
  #     route_key              = route_settings.value.route_key
  #     throttling_burst_limit = try(route_settings.value.throttling_burst_limit, null)
  #     throttling_rate_limit  = try(route_settings.value.throttling_rate_limit, null)
  #   }
  # }



  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }
}

resource "aws_apigatewayv2_authorizer" "cognito_authorizer" {
  api_id           = var.api_id
  name             = var.cognito_authorizer_name
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    issuer   = var.cognito_issuer
    audience = [var.cognito_audience]
  }
}


output "TURTIL-APP_base_url" {
  value = aws_apigatewayv2_stage.this
}


resource "aws_lambda_permission" "invoke_permission" {
  for_each = { for lambda in var.lambda_functions : lambda.function_name => lambda }

  statement_id  = "AllowExecutionFromAPIGateway-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = each.value.source_arn
}



