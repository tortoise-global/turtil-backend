module "student_images_bucket" {
  source        = "./modules/buckets"
  bucket_name   = var.student_images_bucket_name[terraform.workspace]["student_document"]
  force_destroy = terraform.workspace == "prod" ? false : true
  tags = {
    Environment = lookup(var.bucket_env_tags_image_upload, terraform.workspace)
  }
}


output "student_images_bucket_id" {
  value = module.student_images_bucket.bucket_id
}

output "student_images_bucket_arn" {
  value = module.student_images_bucket.bucket_arn
}
