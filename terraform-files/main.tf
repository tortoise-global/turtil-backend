
terraform {
  # Run init/plan/apply with "backend" commented-out (ueses local backend) to provision Resources (Bucket, Table)
  # Then uncomment "backend" and run init, apply after Resources have been created (uses AWS)

  /*
  required_version = "= 1.6.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.53.0" # Use the desired version here
    }
  }
  */

  backend "s3" {
    bucket = "turtul-cms-terraform-be"
    key    = "tf-infra/terraform.tfstate"
    region = "ap-south-1"
  }
}


provider "aws" {
  region = "ap-south-1"
}