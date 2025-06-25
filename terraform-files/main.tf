terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60.0"
    }
  }

  backend "s3" {
    bucket         = "turtil-backend-dev-ap-south-1"
    key            = "tf-infra/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "turtil-backend-dev-ap-south-1-terraform-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "turtil-backend"
      Environment = "dev"
      ManagedBy   = "terraform"
      Region      = var.aws_region
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "zone-type"
    values = ["availability-zone"]
  }
}

# AMI Creation Module - Create if not exists
module "ami" {
  source = "./modules/ami"

  environment = "dev"
  region      = var.aws_region

  tags = local.common_tags
}

# VPC and Networking Module
module "vpc" {
  source = "./modules/vpc"

  environment        = "dev"
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)

  tags = local.common_tags
}

# RDS Module with Destroy Protection
module "rds" {
  source = "./modules/rds"

  environment           = "dev"
  instance_class        = "db.t4g.small"
  database_name         = "turtil-backend-dev"
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnet_ids
  vpc_security_group_id = module.vpc.rds_security_group_id

  tags = local.common_tags
}

# Storage Module (S3)
module "storage" {
  source = "./modules/storage"

  environment = "dev"

  tags = local.common_tags
}

# Container Registry (ECR)
module "ecr" {
  source = "./modules/ecr"

  environment = "dev"

  tags = local.common_tags
}

# Compute Module (EC2/ASG/ALB)
module "compute" {
  source = "./modules/compute"

  environment      = "dev"
  custom_ami_id    = module.ami.ami_id
  instance_type    = "t4g.medium"
  min_size         = 1
  max_size         = 2
  desired_capacity = 1

  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  private_subnet_ids    = module.vpc.private_subnet_ids
  alb_security_group_id = module.vpc.alb_security_group_id
  ec2_security_group_id = module.vpc.ec2_security_group_id

  # Application Configuration
  database_url       = module.rds.database_url
  s3_bucket_name     = module.storage.bucket_name
  ecr_repository_url = module.ecr.repository_url

  # Environment Variables from GitHub Secrets
  secret_key            = var.secret_key
  aws_access_key_id     = var.aws_access_key_id
  aws_secret_access_key = var.aws_secret_access_key
  upstash_redis_url     = var.upstash_redis_url
  upstash_redis_token   = var.upstash_redis_token
  aws_ses_from_email    = var.aws_ses_from_email

  tags = local.common_tags
}

# Local values
locals {
  common_tags = {
    Project     = "turtil-backend"
    Environment = "dev"
    ManagedBy   = "terraform"
    Region      = var.aws_region
  }
}
