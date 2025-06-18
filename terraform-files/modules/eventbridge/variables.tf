
variable "schedule_name" {
  description = "Name of the EventBridge schedule"
  type        = string
}

variable "schedule_description" {
  description = "Description of the EventBridge schedule"
  type        = string
  default     = "Schedule for invoking the Lambda function"
}

variable "schedule_expression" {
  description = "Schedule expression for the EventBridge rule"
  type        = string
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function to be invoked"
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function to be invoked"
  type        = string
}
