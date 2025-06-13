variable "api_id" {
  description = "The ID of the API Gateway"
  type        = string
}

variable "integrations" {
  description = "List of Lambda integrations"
  type = list(object({
    name = string
    uri  = string
  }))
}

variable "routes" {
  description = "List of API Gateway routes"
  type = list(object({
    route_key        = string
    integration_name = string
    authorize         = bool
  }))
}

variable "lambda_functions" {
  description = "List of Lambda functions and their ARNs to grant permissions to"
  type = list(object({
    function_name = string
    source_arn    = string
  }))
}


variable "stage_name" {
  description = "The name of the API Gateway stage"
  type        = string
}

variable "log_retention_days" {
  description = "The number of days to retain logs in CloudWatch"
  type        = number
}

variable "cognito_authorizer_name" {
  description = "The name of the Cognito authorizer"
  type        = string
}

variable "cognito_issuer" {
  description = "The issuer URL for Cognito"
  type        = string
}

variable "cognito_audience" {
  description = "The audience for Cognito"
  type        = string
}

