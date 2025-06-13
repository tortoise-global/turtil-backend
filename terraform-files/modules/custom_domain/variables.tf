variable "domain_name" {
  //description = "The domain name for the TLS certificate and API Gateway domain"
  //type        = string
  //default     = "devcicd.turtil.co"

  type = map(string)

  default = {
    "dev"  = "devapi.std.turtil.co"
    "prod" = "api.std.turtil.co"
    "test" = "testapi.std.turtil.co"
  }
}



variable "validation_method" {
  //description = "The validation method for the TLS certificate"
  //type        = string
  //default     = "DNS"

  type = map(string)

  default = {
    "dev"  = "DNS"
    "prod" = "DNS"
    "test" = "DNS"
  }
}



variable "route53_zone_name" {
  //description = "The name of the Route53 hosted zone"
  //type        = string
  //default     = "turtil.co"

  type = map(string)

  default = {
    "dev"  = "turtil.co"
    "prod" = "turtil.co"
    "test" = "turtil.co"
  }
}

variable "route53_ttl" {
  //description = "The TTL for the Route53 record"
  //type        = number
  //default     = 60

  type = map(number)

  default = {
    "dev"  = 60
    "prod" = 60
    "test" = 60
  }
}



variable "endpoint_type" {
  //description = "The type of endpoint for the API Gateway domain"
  //type        = string
  //default     = "REGIONAL"

  type = map(string)

  default = {
    "dev"  = "REGIONAL"
    "prod" = "REGIONAL"
    "test" = "REGIONAL"
  }
}


variable "security_policy" {
  //description = "The security policy for the API Gateway domain"
  //type        = string
  //default     = "TLS_1_2"

  type = map(string)

  default = {
    "dev"  = "TLS_1_2"
    "prod" = "TLS_1_2"
    "test" = "TLS_1_2"
  }
}

variable "api_id" {
  description = "The ID of the API Gateway"
  type        = string
}

variable "stage_id" {
  description = "The ID of the deployment stage"
  type        = string
}


variable "api_mapping_key" {
  //description = "The API mapping key for a specific version"
  //type        = string
  //default     = "v1"

  type = map(string)

  default = {
    "dev"  = "dev/v1"
    "prod" = "prod/v1"
    "test" = "test/v1"
  }

}


variable "create_domain" {
  type        = map(bool)
  description = "Whether to create the custom domain for each environment"
  default = {
    dev  = true
    test = true
    prod = true
  }
}

###### 

variable "api_id_2" {
  description = "The API Gateway ID for the second API."
  type        = string
}

variable "stage_id_2" {
  description = "The stage name for the second API Gateway."
  type        = string
}

variable "api_mapping_key_2" {
  type = map(string)

  default = {
    "dev"  = "dev/sec"
    "prod" = "prod/sec"
    "test" = "test/sec"
  }
}


#### alumni ##

variable "api_id_3" {
  description = "The API Gateway ID for the third API."
  type        = string
}

variable "stage_id_3" {
  description = "The stage name for the third API Gateway."
  type        = string
}

variable "api_mapping_key_3" {
  type = map(string)

  default = {
    "dev"  = "dev/alumni"
    "prod" = "prod/alumni"
    "test" = "test/alumni"
  }
}
