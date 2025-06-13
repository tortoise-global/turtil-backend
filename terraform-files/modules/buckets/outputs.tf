output "create_bucket_id" {
  description = "The ID of the S3 bucket"
  value       = aws_s3_bucket.these.id
}

output "create_bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = aws_s3_bucket.these.arn
}
