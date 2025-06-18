variable "student_images_bucket_name" {
  type = map(map(string))
  default = {
    "dev" = {
      "student_document" = "cms-images-upload-1"
    },
    "prod" = {
      "student_document" = "cms-images-upload-1"
    }
    "test" = {
      "student_document" = "cms-images-upload-1"
    }
  }
}


variable "bucket_policy_name_image_upload" {
  type = map(string)

  default = {
    "dev"  = "arn:aws:s3:::cms-images-upload-1/*"
    "prod" = "arn:aws:s3:::cms-images-upload-1/*"
    "test" = "arn:aws:s3:::cms-images-upload-1/*"
  }
}


variable "bucket_env_tags_image_upload" {
  type = map(string)

  default = {
    "dev"  = "dev"
    "prod" = "prod"
    "test" = "test"
  }
}