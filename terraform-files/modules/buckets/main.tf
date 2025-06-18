resource "aws_s3_bucket" "these" {
  bucket        = var.bucket_name
  force_destroy = var.force_destroy # Enable force destroy to delete all objects when bucket is destroyed

  tags = var.tags
}

output "bucket_id" {
  value = aws_s3_bucket.these.id
}

output "bucket_arn" {
  value = aws_s3_bucket.these.arn
}
