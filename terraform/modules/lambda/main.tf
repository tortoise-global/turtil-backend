data "aws_s3_bucket" "existing_bucket" {
  bucket = lookup(var.lambda_bucket_name, terraform.workspace)
}

locals {
  bucket_exists = can(data.aws_s3_bucket.existing_bucket)
}

resource "aws_s3_bucket" "lambda_bucket" {
  count         = local.bucket_exists ? 0 : 1
  bucket        = lookup(var.lambda_bucket_name, terraform.workspace)
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "lambda_bucket" {
  bucket                  = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_lambda_function" "lambda_function" {
  function_name    = var.lambda_function_prefix
  s3_bucket        = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
  s3_key           = aws_s3_object.lambda_code.key
  runtime          = lookup(var.lambda_runtime, terraform.workspace)
  handler          = lookup(var.lambda_handler, terraform.workspace)
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  role             = var.role_arn
  timeout          = lookup(var.lambda_timeout, terraform.workspace)
  memory_size      = 1024

  layers = var.layers

  dynamic "environment" {
    for_each = length(keys(var.shared_environment_variables)) > 0 || length(keys(var.lambda_environment_variables)) > 0 ? [1] : []
    content {
      variables = merge(var.shared_environment_variables, var.lambda_environment_variables)
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.lambda_function.function_name}"
  retention_in_days = lookup(var.log_retention, terraform.workspace)
}

### from here error logs start
#Create CloudWatch Metric Filter for Errors with Lambda function name
#Create CloudWatch Metric Filter for Errors with Lambda function name
resource "aws_cloudwatch_log_metric_filter" "lambda_error_metric" {
  name           = "${aws_lambda_function.lambda_function.function_name}-ErrorMetric"
  log_group_name = aws_cloudwatch_log_group.lambda_log_group.name

  # Correct pattern syntax for CloudWatch Logs
  pattern = "?ERROR ?Error ?Exception ?exception ?Failed ?failed"

  metric_transformation {
    name      = "${aws_lambda_function.lambda_function.function_name}-ErrorCount"
    namespace = "LambdaMetrics"
    value     = "1"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Create CloudWatch Alarm for Errors
resource "aws_cloudwatch_metric_alarm" "lambda_error_alarm" {
  alarm_name          = "${aws_lambda_function.lambda_function.function_name}-ErrorAlarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "${aws_lambda_function.lambda_function.function_name}-ErrorCount"
  namespace           = "LambdaMetrics"
  period              = "86400"
  statistic           = "Sum"
  threshold           = "15"
  alarm_description   = "Alarm for errors in Lambda function: ${aws_lambda_function.lambda_function.function_name}"
  actions_enabled     = true

  alarm_actions = [aws_sns_topic.lambda_error_sns.arn]

  lifecycle {
    create_before_destroy = true
  }
}

# Create SNS Topic for Error Notifications with a display name
resource "aws_sns_topic" "lambda_error_sns" {
  name         = "LambdaErrorNotifications"
  display_name = "Lambda Error Alerts"

  lifecycle {
    create_before_destroy = true
  }
}

# Add SNS Topic Policy to ensure CloudWatch can publish to it
resource "aws_sns_topic_policy" "lambda_error_sns_policy" {
  arn = aws_sns_topic.lambda_error_sns.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "cloudwatch.amazonaws.com" }
        Action    = "sns:Publish"
        Resource  = aws_sns_topic.lambda_error_sns.arn
      }
    ]
  })

  lifecycle {
    create_before_destroy = true
  }
}

# SNS Subscription for Email Notifications
# resource "aws_sns_topic_subscription" "email_subscription" {
#   topic_arn = aws_sns_topic.lambda_error_sns.arn
#   protocol  = "email"
#   endpoint  = lookup(var.notification_email, terraform.workspace)

#   filter_policy = jsonencode({
#     lambda_function = [aws_lambda_function.lambda_function.function_name]
#   })
# }

# SNS Subscription for Email Notifications
# resource "aws_sns_topic_subscription" "email_subscription" {
#   for_each  = toset(var.notification_emails) # Convert the list to a set for iteration
#   topic_arn = aws_sns_topic.lambda_error_sns.arn
#   protocol  = "email"
#   endpoint  = each.value

#   filter_policy = jsonencode({
#     lambda_function = [aws_lambda_function.lambda_function.function_name]
#   })

#   lifecycle {
#     create_before_destroy = true
#   }
# }


# SNS Subscription for Email Notifications
# toset(var.notification_emails)
resource "aws_sns_topic_subscription" "email_subscription" {
  for_each  = toset(lookup(var.notification_emails, terraform.workspace, []))
  topic_arn = aws_sns_topic.lambda_error_sns.arn
  protocol  = "email"
  endpoint  = each.value

  # Remove the filter_policy since it might be causing the conflict
  # filter_policy = jsonencode({
  #   lambda_function = [aws_lambda_function.lambda_function.function_name]
  # })

  lifecycle {
    create_before_destroy = true
    # Add ignore_changes to prevent unnecessary updates
    ignore_changes = [
      filter_policy
    ]
  }
}


# Output the SNS topic ARN for verification
output "sns_topic_arn" {
  value       = aws_sns_topic.lambda_error_sns.arn
  description = "The ARN of the SNS topic for Lambda error notifications"
}

### from here error logs end



data "archive_file" "lambda_code" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${var.output_path_prefix}/${var.prefix}_lambda_code.zip"
}

resource "aws_s3_object" "lambda_code" {
  bucket = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
  key    = "${var.prefix}/${lookup(var.lambda_s3_keys, terraform.workspace)}"
  source = data.archive_file.lambda_code.output_path
  etag   = filemd5(data.archive_file.lambda_code.output_path)
}

output "function_name" {
  value = aws_lambda_function.lambda_function.function_name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.lambda_log_group.name
}













































# data "aws_s3_bucket" "existing_bucket" {
#   bucket = lookup(var.lambda_bucket_name, terraform.workspace)
# }

# locals {
#   bucket_exists = can(data.aws_s3_bucket.existing_bucket)
# }

# resource "aws_s3_bucket" "lambda_bucket" {
#   count         = local.bucket_exists ? 0 : 1
#   bucket        = "dev-res-lambda"
#   force_destroy = false
# }

# resource "aws_s3_bucket_public_access_block" "lambda_bucket" {
#   bucket                  = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
#   block_public_acls       = true
#   block_public_policy     = true
#   ignore_public_acls      = true
#   restrict_public_buckets = true
# }

# resource "aws_lambda_function" "lambda_function" {
#   function_name    = "${var.prefix}-${var.lambda_function_prefix}"
#   s3_bucket        = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
#   s3_key           = aws_s3_object.lambda_code.key
#   runtime          = lookup(var.lambda_runtime, terraform.workspace)
#   handler          = lookup(var.lambda_handler, terraform.workspace)
#   source_code_hash = data.archive_file.lambda_code.output_base64sha256
#   role             = var.role_arn
#   timeout          = lookup(var.lambda_timeout, terraform.workspace)

#   layers = var.layers

#   dynamic "environment" {
#     for_each = length(keys(var.shared_environment_variables)) > 0 || length(keys(var.lambda_environment_variables)) > 0 ? [1] : []
#     content {
#       variables = merge(var.shared_environment_variables, var.lambda_environment_variables)
#     }
#   }
# }

# resource "aws_cloudwatch_log_group" "lambda_log_group" {
#   name              = "/aws/lambda/${var.prefix}-${aws_lambda_function.lambda_function.function_name}"
#   retention_in_days = lookup(var.log_retention, terraform.workspace)
# }

# data "archive_file" "lambda_code" {
#   type        = "zip"
#   source_dir  = var.source_dir
#   output_path = "${var.output_path_prefix}/${var.prefix}_lambda_code.zip"
# }

# resource "aws_s3_object" "lambda_code" {
#   bucket = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
#   key    = "${var.prefix}/${lookup(var.lambda_s3_keys, terraform.workspace)}"
#   source = data.archive_file.lambda_code.output_path
#   etag   = filemd5(data.archive_file.lambda_code.output_path)
# }



# output "function_name" {
#   value = aws_lambda_function.lambda_function.function_name
# }

# output "log_group_name" {
#   value = aws_cloudwatch_log_group.lambda_log_group.name
# }



# variable "source_dir" {
#   description = "The directory containing the Lambda function source code."
#   type        = string
# }


# output "function_name" {
#   value = aws_lambda_function.lambda_function.function_name
# }

# output "log_group_name" {
#   value = aws_cloudwatch_log_group.lambda_log_group.name
# }


# variable "source_dir" {
#   description = "The directory containing the Lambda function source code."
#   type        = string
# }

# variable "output_path_prefix" {
#   description = "The prefix path for the Lambda code zip output."
#   type        = string
# }

# variable "prefix" {
#   description = "Prefix for resource names."
#   type        = string
# }

# # Ensure that the source directory is not empty
# locals {
#   source_files = fileset(var.source_dir, "**")
# }

# resource "null_resource" "check_source_dir" {
#   count = length(local.source_files) > 0 ? 0 : 1

#   provisioner "local-exec" {
#     command = "echo 'Error: The source directory is empty. Ensure that the directory contains files.' && exit 1"
#   }
# }

# data "archive_file" "lambda_code" {
#   depends_on  = [null_resource.check_source_dir]
#   type        = "zip"
#   source_dir  = var.source_dir
#   output_path = "${var.output_path_prefix}/${var.prefix}_lambda_code.zip"
# }

# resource "aws_s3_object" "lambda_code" {
#   bucket = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
#   key    = "${var.prefix}/${lookup(var.lambda_s3_keys, terraform.workspace)}"
#   source = data.archive_file.lambda_code.output_path
#   etag   = filemd5(data.archive_file.lambda_code.output_path)
# }

# output "function_name" {
#   value = aws_lambda_function.lambda_function.function_name
# }

# output "log_group_name" {
#   value = aws_cloudwatch_log_group.lambda_log_group.name
# }

