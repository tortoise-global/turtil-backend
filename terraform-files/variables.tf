variable "ecr_repository_name" {
  type = map(string)
  default = {
    "dev"  = "dev-cms-api-repo"
    "test" = "test-cms-api-repo"
    "prod" = "prod-cms-api-repo"
  }
}


variable "ecr_env_tags" {
  type = map(string)
  default = {
    "dev"  = "dev"
    "test" = "test"
    "prod" = "prod"
  }

}
