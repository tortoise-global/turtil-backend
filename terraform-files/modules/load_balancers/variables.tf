variable "alb_name" {
  description = "Name of the Application Load Balancer"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC to use (if empty, uses default VPC)"
  type        = string
  default     = ""
}

variable "target_group_port" {
  description = "Port for the target group to route traffic to"
  type        = number
  default     = 80
}

variable "health_check_path" {
  description = "Path for the target group health check"
  type        = string
  default     = "/"
}

variable "ec2_instance_id" {
  description = "ID of the EC2 instance to attach to the target group (optional, used only if not using ASG)"
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default     = {}
}