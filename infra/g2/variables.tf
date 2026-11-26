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

variable "eks_version" {
  description = "Kubernetes minor version in EKS standard support; choose before planning"
  type        = string

  validation {
    condition     = can(regex("^1\\.[0-9]+$", var.eks_version))
    error_message = "Use a Kubernetes minor version such as 1.XX."
  }
}

variable "admin_access_cidrs" {
  description = "Administrator public IPv4 addresses allowed to reach the EKS public API, each as /32"
  type        = list(string)

  validation {
    condition = length(var.admin_access_cidrs) > 0 && alltrue([
      for cidr in var.admin_access_cidrs : can(cidrnetmask(cidr)) && endswith(cidr, "/32")
    ])
    error_message = "Supply at least one valid IPv4 /32 administrator CIDR."
  }
}

variable "data_bucket_name" {
  description = "Existing G1 S3 bucket for datasets and G2 results"
  type        = string
}
