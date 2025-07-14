#aurora db instance name
variable "aurora_postgres_name" {
  type = map(string)
  default = {
    "dev"  = "devcms"
    "test" = "testcms"
    "prod" = "prodcms"
  }
}

#aurora database name
variable "db_name" {
  type = map(string)
  default = {
    "dev"  = "devcmsmanagement"
    "test" = "testcmsmanagement"
    "prod" = "prodcmsmanagement"
  }
}

# ACM Certificate Domain Names
variable "acm_domain_names" {
  type = map(string)
  default = {
    dev  = "dev.app.turtil.co"
    test = "test.app.turtil.co"
    prod = "prod.app.turtil.co"
  }
}

# SANs for each environment
variable "acm_san_names" {
  type = map(list(string))
  default = {
    dev  = ["dev.app.turtil.co"]
    test = ["test.app.turtil.co"]
    prod = ["prod.app.turtil.co"]
  }
}

# Hosted Zone IDs (Route 53)
variable "acm_hosted_zone_ids" {
  type = map(string)
  default = {
    dev  = "Z0964890C8UWZEUGAVHY"
    test = "Z0964890C8UWZEUGAVHY"
    prod = "Z0964890C8UWZEUGAVHY"
  }
}

# Tags by Environment
variable "acm_env_tags" {
  type = map(string)
  default = {
    dev  = "dev_app"
    test = "test_app"
    prod = "prod_app"
  }
}

#ecr repository
variable "ecr_repository_name" {
  type = map(string)
  default = {
    "dev"  = "dev-cms-app-repo"
    "test" = "test-cms-app-repo"
    "prod" = "prod-cms-app-repo"
  }
}

#ecr repo tags
variable "ecr_env_tags" {
  type = map(string)
  default = {
    "dev"  = "dev"
    "test" = "test"
    "prod" = "prod"
  }
  
}




variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Must be dev, test, or prod"
  }
}

#vpc for ecs
variable "vpc_id" {
  type = map(string)
  default = {
    dev  = "vpc-0d3f7fc807218d15b"
    test = "vpc-0d3f7fc807218d15b"
    prod = "vpc-0d3f7fc807218d15b"
  }
}


#subnet for ecs 
variable "subnet_a_id" {
  type = map(string)
  default = {
    dev  = "subnet-00fe2bd0c30a0efd5"
    test = "subnet-0adcb03cea7476613"
    prod = "subnet-0ac9b6ee245d3e9eb"
  }
}

variable "subnet_b_id" {
  type = map(string)
  default = {
    dev  = "subnet-0adcb03cea7476613"
    test = "subnet-00fe2bd0c30a0efd5"
    prod = "subnet-00fe2bd0c30a0efd5"
  }
}


variable "subnet_c_id" {
  type = map(string)
  default = {
    dev  = "subnet-0ac9b6ee245d3e9eb"
    test = "subnet-0ac9b6ee245d3e9eb"
    prod = "subnet-0adcb03cea7476613"
  }
}

#domain name for ecs 
variable "domain" {
  type = map(string)
  default = {
    
    dev  = "dev.app.turtil.co"
    test =  "test.app.turtil.co"
    prod = "prod.app.turtil.co"
  }
}


#minimum capacity for ecs scaling
variable "min_capacity" {
    type = map(number)
  default = {
    
    dev  = 1
    test = 1
    prod =1
  }
}

#maximum capacity for ecs scaling

variable "max_capacity" {
    type = map(number)
  default = {
    
    dev  = 2
    test =  2
    prod = 2
  }
}



variable "load_balancer"{
      type = map(string)
  default = {
    
    dev  = "dev-app-load-balance"
    test =  "test-app-load-balance"
    prod = "prod-app-load-balance"
  }
}



variable "target_group"{
          type = map(string)
  default = {
    
    dev  = "dev-app-tg"
    test =  "test-app-tg"
    prod = "prod-app-tg"
  }
}


variable "ClusterName" {
    type = map(string)
  default = {
    
    dev  = "cms-app-dev"
    test =  "cms-app-test"
    prod = "cms-app-prod"
  }
}