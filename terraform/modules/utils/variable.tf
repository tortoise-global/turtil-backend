variable "random_pet_prefix" {
  description = "Prefix for the random pet resource"
  type        = string
  default     = "resource"
}

variable "random_pet_length" {
  description = "Length of the random pet suffix"
  type        = number
  default     = 2
}
