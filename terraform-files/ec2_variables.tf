variable "ec2_instance_name" {
  type = map(map(string))
  default = {
    "dev" = {
      "example_instance"  = "cms-ubuntu-ec2",
      "example_instance2" = "cms-ubuntu-ec2-2"
    },
    "test" = {
      "example_instance"  = "test-ubuntu-ec2",
      "example_instance2" = "test-ubuntu-ec2-2"
    },
    "prod" = {
      "example_instance"  = "prod-ubuntu-ec2",
      "example_instance2" = "prod-ubuntu-ec2-2"
    }
  }
}

variable "ec2_architecture" {
  type = map(string)
  default = {
    "dev"  = "arm64" # x86
    "test" = "arm64" # x86
    "prod" = "arm64" # ARM (Graviton)
  }
}

variable "ec2_instance_type" {
  type = map(string)
  default = {
    "dev"  = "t4g.medium" # x86
    "test" = "t4g.medium" # x86
    "prod" = "t4g.medium" # ARM
  }
}

variable "ec2_key_name" {
  type = map(string)
  default = {
    "dev"  = "the_test_key_pair"
    "test" = "the_test_key_pair"
    "prod" = "the_test_key_pair"
  }
}

variable "ec2_availability_zone" {
  type = map(string)
  default = {
    "dev"  = "ap-south-1a"
    "test" = "ap-south-1a"
    "prod" = "ap-south-1a"
  }
}

variable "ec2_ami_owner" {
  type = map(string)
  default = {
    "dev"  = "099720109477" # Canonical for Ubuntu
    "test" = "099720109477"
    "prod" = "099720109477"
  }
}

variable "ec2_ami_name_filter" {
  type = map(string)
  default = {
    "dev"  = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-*"
    "test" = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-*"
    "prod" = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-*"
  }
}

variable "ec2_root_block_device_size" {


  type = map(number)
  default = {
    "dev"  = 8
    "test" = 8
    "prod" = 20 # Larger disk for prod
  }
}

variable "ec2_ingress_rules" {
  type = map(list(object({
    description = string
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_block  = string
  })))
  default = {
    "dev" = [
      {
        description = "SSH from anywhere"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      },
      {
        description = "HTTP from anywhere"
        from_port   = 80
        to_port     = 80
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      },
      {
        description = "FastAPI port 8000"
        from_port   = 8000
        to_port     = 8000
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      }
    ],
    "test" = [
      {
        description = "SSH from anywhere"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      },
      {
        description = "HTTP from anywhere"
        from_port   = 80
        to_port     = 80
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      },
      {
        description = "FastAPI port 8000"
        from_port   = 8000
        to_port     = 8000
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      }
    ],
    "prod" = [
      {
        description = "SSH from restricted CIDR"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_block  = "203.0.113.0/24" # Replace with your IP range
      },
      {
        description = "HTTP from anywhere"
        from_port   = 80
        to_port     = 80
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      },
      {
        description = "FastAPI port 8000 IPv4"
        from_port   = 8000
        to_port     = 8000
        protocol    = "tcp"
        cidr_block  = "0.0.0.0/0"
      },
      {
        description = "FastAPI port 8000 IPv6"
        from_port   = 8000
        to_port     = 8000
        protocol    = "tcp"
        cidr_block  = "::/0"
      }
    ]
  }
}

variable "ec2_env_tags" {
  type = map(string)
  default = {
    "dev"  = "dev"
    "test" = "test"
    "prod" = "prod"
  }
}

variable "asg_min_size" {
  type = map(number)
  default = {
    "dev"  = 1
    "test" = 1
    "prod" = 2
  }
}

variable "asg_max_size" {
  type = map(number)
  default = {
    "dev"  = 1
    "test" = 4
    "prod" = 8
  }
}

variable "asg_desired_capacity" {
  type = map(number)
  default = {
    "dev"  = 1
    "test" = 2
    "prod" = 4
  }
}

variable "asg_target_cpu_utilization" {
  type = map(number)
  default = {
    "dev"  = 50
    "test" = 50
    "prod" = 70
  }
}

# Environment variables passed from GitHub Actions
variable "app_database_url" {
  description = "Database URL"
  type        = string
  sensitive   = true
}

variable "app_secret_key" {
  description = "Secret key"
  type        = string
  sensitive   = true
}

variable "app_aws_access_key_id" {
  description = "AWS Access Key ID"
  type        = string
  sensitive   = true
}

variable "app_aws_secret_access_key" {
  description = "AWS Secret Access Key"
  type        = string
  sensitive   = true
}

variable "app_s3_bucket_name" {
  description = "S3 bucket name"
  type        = string
}

variable "app_upstash_redis_url" {
  description = "Upstash Redis URL"
  type        = string
  sensitive   = true
}

variable "app_upstash_redis_token" {
  description = "Upstash Redis Token"
  type        = string
  sensitive   = true
}

variable "app_gmail_email" {
  description = "Gmail email"
  type        = string
  sensitive   = true
}

variable "app_gmail_app_password" {
  description = "Gmail app password"
  type        = string
  sensitive   = true
}
