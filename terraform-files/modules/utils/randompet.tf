resource "random_pet" "resource_name" {
  prefix = var.random_pet_prefix
  length = var.random_pet_length
}
