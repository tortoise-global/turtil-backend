variable "lambda_function_name" {
  description = "Name of the Lambda function"

  type = map(string)

  default = {
    "dev"  = "DEV-USER-MANAGEMENT-TURTIL-APP"
    "prod" = "PROD-USER-MANAGEMENT-TURTIL-APP"
    "test" = "TEST-USER-MANAGEMENT-TURTIL-APP"
  }
}


variable "lambda_runtime" {
  description = "Runtime for the Lambda function"
  type        = map(string)

  default = {
    "dev"  = "python3.11"
    "prod" = "python3.11"
    "test" = "python3.11"
  }
}


variable "lambda_handler" {
  //type    = string
  //default = "lambda_fun.lambda_handler"

  type = map(string)

  default = {
    "dev"  = "lambda_fun.lambda_handler"
    "prod" = "lambda_fun.lambda_handler"
    "test" = "lambda_fun.lambda_handler"
  }
}

variable "lambda_timeout" {
  //type    = number
  //default = 600

  type = map(number)

  default = {
    "dev"  = 900
    "prod" = 900
    "test" = 900
  }
}

variable "source_dir" {
  description = "Directory containing the Lambda function source code"
  type        = string
}

variable "output_path_prefix" {
  description = "Prefix for the output path of the zipped Lambda code"
  type        = string
}


variable "lambda_s3_keys" {
  description = "S3 key for the Lambda function code"
  type        = map(string)
  default = {
    "dev"  = "DEV-USER-MANAGEMENT-LAMBDA.zip"
    "prod" = "PROD-USER-MANAGEMENT-LAMBDA.zip"
    "test" = "TEST-USER-MANAGEMENT-LAMBDA.zip"
  }
}

variable "role_arn" {
  description = "ARN of the IAM role for the Lambda function"
  type        = string
}


variable "log_retention" {
  //type    = number
  //default = 14

  type = map(number)

  default = {
    "dev"  = 1
    "prod" = 7
    "test" = 1
  }
}

variable "layers" {
  description = "List of Lambda layers"
  type        = list(string)
  default     = []
}


variable "lambda_function_prefix" {
  description = "Prefix for the Lambda function name"
  type        = string
  default     = "lambda-func"
}

variable "shared_environment_variables" {
  description = "Shared environment variables for all Lambda functions"
  type        = map(string)
  default     = {}
}

variable "lambda_environment_variables" {
  description = "Lambda-specific environment variables"
  type        = map(string)
  default     = {}
}

variable "prefix" {
  description = "Prefix for Lambda and related resources"
  type        = string
}



variable "lambda_bucket_name" {
  description = "Name of the Lambda bucket"

  type = map(string)

  default = {
    "dev"  = "dev-res-lambda"
    "prod" = "prod-res-lambda"
    "test" = "test-res-lambda"
  }
}



# variable "notification_email" {

#   description = "Name of the notification email"

#   type = map(string)

#   default = {
#     "dev"  = "abhishek.jn@turtil.co"
#     "prod" = "rajsekhar.s@turtil.co"
#     "test" = "abhishek.jn@turtil.co"
#   }
# }


# variable "notification_emails" {
#   description = "List of email addresses to subscribe to SNS topic"
#   type        = list(string)
#   default     = ["abhishek.jn@turtil.co", "rajsekhar.s@turtil.co", "karthik@turtil.co"]
# }


variable "notification_emails" {
  description = "Map of environment to list of email addresses for SNS subscription"
  type        = map(list(string)) # Changed from list(string) to map(list(string))
  default = {
    "dev" : []
    "prod" : ["abhishek.jn@turtil.co", "rajsekhar.s@turtil.co", "karthik@turtil.co"]
    "test" : []
  }
}

