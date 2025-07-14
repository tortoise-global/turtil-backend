terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket               = "ecs-cluster-app"
    key                  = "terraform.tfstate"
    workspace_key_prefix = "ecs"
    region               = "ap-south-1"
    encrypt              = true
  }
}

provider "aws" {
  region = "ap-south-1"
}