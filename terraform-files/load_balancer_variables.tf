variable "alb_name" {
  type = map(string)
  default = {
    "dev"  = "dev-cms-alb"
    "test" = "test-cms-alb"
    "prod" = "prod-cms-alb"
  }
}

variable "alb_target_group_port" {
  type = map(number)
  default = {
    "dev"  = 80
    "test" = 80
    "prod" = 80
  }
}

variable "alb_health_check_path" {
  type = map(string)
  default = {
    "dev"  = "/health/simple"
    "test" = "/health/simple"
    "prod" = "/health/simple"
  }
}