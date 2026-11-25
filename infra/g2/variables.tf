variable "aws_region" {
  description = "AWS Region for G2"
  type        = string
  default     = "ap-northeast-2"
}

variable "name" {
  description = "Prefix for G2 networking resources"
  type        = string
  default     = "shared-gpu-g2"
}

variable "vpc_cidr" {
  description = "G2 VPC IPv4 CIDR, separate from existing G1 VPC"
  type        = string
  default     = "10.42.0.0/16"
}

variable "availability_zones" {
  description = "Two distinct availability zones for G2 private/public subnets"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]

  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "Choose exactly two distinct availability zones."
  }
}
