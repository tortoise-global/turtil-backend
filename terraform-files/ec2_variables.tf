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



variable "ec2_user_data" {
  type = map(string)
  default = {
    "dev" = <<-EOT
      #!/bin/bash
      # Install Docker from official repository
      sudo apt-get update -y
      sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
      
      # Ensure SSM agent is running (pre-installed on Ubuntu AMI)
      sudo systemctl enable amazon-ssm-agent
      sudo systemctl start amazon-ssm-agent
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
      sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
      sudo apt-get update -y
      sudo apt-get install -y docker-ce docker-ce-cli containerd.io
      sudo systemctl start docker
      sudo usermod -aG docker ubuntu  # Ubuntu uses "ubuntu" user

      newgrp docker

      # Install aws-cli
      sudo apt install -y awscli

      # Install Amazon ECR Credential Helper
      sudo apt-get install -y amazon-ecr-credential-helper
      sudo mkdir -p /root/.docker
      sudo mkdir -p /home/ubuntu/.docker
      echo '{"credsStore": "ecr-login"}' | sudo tee /root/.docker/config.json
      echo '{"credsStore": "ecr-login"}' | sudo tee /home/ubuntu/.docker/config.json

      # Install Docker Compose
      sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
      sudo chmod +x /usr/local/bin/docker-compose

      # Install Nginx
      sudo apt-get install -y nginx
      sudo systemctl start nginx
      sudo systemctl enable nginx

      # Configure Nginx as a reverse proxy
      cat <<'EOF' | sudo tee /etc/nginx/sites-available/default
      server {
          listen 80 default_server;
          listen [::]:80 default_server;

          root /var/www/html;

          index index.html index.htm index.nginx-debian.html;

          server_name _;

          location / {
              add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE'; 
              add_header 'Access-Control-Allow-Headers' 'Authorization'; 
              add_header 'Access-Control-Allow-Origins' '*'; 
              proxy_pass http://localhost:8000;
              proxy_set_header Host \$host;
              proxy_set_header X-Real-IP \$remote_addr;
              proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto \$scheme;
          }
      }
      EOF

     

      # Test Nginx configuration and reload
      sudo nginx -t
      sudo systemctl reload nginx

      # Pull latest image from ECR (IAM role handles authentication)
      ECR_URI="033464272864.dkr.ecr.ap-south-1.amazonaws.com"

      aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin $ECR_URI

      docker pull $ECR_URI/dev-cms-api-repo:latest

      # Generate docker-compose.yml
      cat <<EOF > /home/ubuntu/docker-compose.yml
      services:
        web:
          image: $ECR_URI/dev-cms-api-repo:latest
          ports:
            - "8000:8000"
          env_file:
            - /home/ubuntu/.env
          command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
          restart: always
          networks:
            - default

      networks:
        default:
          driver: bridge

      EOF

      # Wait for .env file to be created by GitHub Actions
      echo "Waiting for .env file from deployment..."
      
      # Start the app (will be restarted when .env is deployed)
      docker-compose -f /home/ubuntu/docker-compose.yml up -d
    EOT
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

variable "app_algorithm" {
  description = "JWT algorithm"
  type        = string
  default     = "HS256"
}

variable "app_access_token_expire_minutes" {
  description = "Access token expiration time in minutes"
  type        = string
  default     = "30"
}

variable "app_project_name" {
  description = "Project name"
  type        = string
  default     = "Turtil Backend"
}

variable "app_version" {
  description = "Application version"
  type        = string
  default     = "1.0.0"
}

variable "app_log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "app_rate_limit_calls" {
  description = "Rate limit calls per period"
  type        = string
  default     = "100"
}

variable "app_rate_limit_period" {
  description = "Rate limit period in seconds"
  type        = string
  default     = "60"
}

variable "app_otp_secret" {
  description = "OTP secret key"
  type        = string
  sensitive   = true
  default     = "123456"
}

variable "app_otp_expiry_minutes" {
  description = "OTP expiration time in minutes"
  type        = string
  default     = "5"
}

variable "app_redis_user_cache_ttl" {
  description = "Redis user cache TTL in seconds"
  type        = string
  default     = "300"
}

variable "app_redis_blacklist_ttl" {
  description = "Redis blacklist TTL in seconds"
  type        = string
  default     = "86400"
}
