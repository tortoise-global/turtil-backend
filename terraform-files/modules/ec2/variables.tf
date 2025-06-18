variable "instance_name" {
  description = "Name of the EC2 instance"
  type        = string
}

variable "instance_type" {
  description = "Type of EC2 instance (e.g., t2.micro)"
  type        = string
  default     = "t2.micro"
}

variable "key_name" {
  description = "Name of the SSH key pair to use for the instance"
  type        = string
}

variable "availability_zone" {
  description = "Availability zone for the subnet"
  type        = string
  default     = "ap-south-1a"
}

variable "vpc_id" {
  description = "ID of the VPC to use (if empty, uses default VPC)"
  type        = string
  default     = ""
}

variable "ami_owner" {
  description = "Owner of the AMI (e.g., '099720109477' for Canonical/Ubuntu)"
  type        = string
  default     = "099720109477"
}

variable "ami_name_filter" {
  description = "Filter for AMI name (e.g., 'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*')"
  type        = string
  default     = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
}

variable "root_block_device_size" {
  description = "Size of the root block device in GB"
  type        = number
  default     = 8
}

variable "ingress_rules" {
  description = "List of ingress rules for the security group"
  type = list(object({
    description = string
    from_port   = number
    to_port     = number
    protocol    = string
    cidr_block  = string
  }))
  default = [
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
    }
  ]
}

variable "user_data" {
  description = "User data script to run on instance launch"
  type        = string
  default     = ""
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default     = {}
}

variable "alb_security_group_id" {
  description = "Security group ID of the ALB to allow traffic from (optional)"
  type        = string
  default     = null
}