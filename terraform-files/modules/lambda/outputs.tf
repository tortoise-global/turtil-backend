# output "lambda_bucket_id" {
#   value = aws_s3_bucket.lambda_bucket.id
# }

# output "lambda_bucket_name" {
#   value = aws_s3_bucket.lambda_bucket.bucket
# }

# output "lambda_arn" {
#   value = aws_lambda_function.lambda_function.arn
# }

# output "lambda_function_name" {
#   value = aws_lambda_function.lambda_function.function_name
# }

# output "lambda_function_arn" {
#   value = aws_lambda_function.lambda_function.arn
# }

# output "lambda_log_group_name" {
#   value = aws_cloudwatch_log_group.lambda_log_group.name
# }



# output "lambda_bucket_id" {
#   value = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.id : aws_s3_bucket.lambda_bucket[0].id
# }

# output "lambda_bucket_name" {
#   value = local.bucket_exists ? data.aws_s3_bucket.existing_bucket.bucket : aws_s3_bucket.lambda_bucket[0].bucket
# }


# output "lambda_bucket_id" {
#   value = aws_s3_bucket.lambda_bucket.id
# }

# output "lambda_bucket_name" {
#   value = aws_s3_bucket.lambda_bucket.bucket
# }

# output "lambda_bucket_name" {
#   value = aws_s3_bucket.lambda_bucket[count.index].bucket
# }


output "lambda_arn" {
  value = aws_lambda_function.lambda_function.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.lambda_function.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.lambda_function.arn
}

output "lambda_log_group_name" {
  value = aws_cloudwatch_log_group.lambda_log_group.name
}