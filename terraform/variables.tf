variable "aws_region" {
  description = "AWS region in which to create the isolated environment."
  type        = string
}

variable "instance_type" {
  description = "ARM64 instance type for the single-host Compose deployment."
  type        = string
  default     = "t4g.small"
}

variable "data_volume_size_gib" {
  description = "Size of the separate encrypted EBS volume for SQLite data. Increase this if the verified backup plus growth needs more space."
  type        = number
  default     = 10

  validation {
    condition     = var.data_volume_size_gib >= 10
    error_message = "Use at least 10 GiB for the application data volume."
  }
}

variable "ssh_ingress_cidr" {
  description = "Your public IPv4 address in CIDR notation, for example 203.0.113.10/32. Never use 0.0.0.0/0 for SSH."
  type        = string

  validation {
    condition     = can(cidrhost(var.ssh_ingress_cidr, 0)) && can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/32$", var.ssh_ingress_cidr))
    error_message = "Set ssh_ingress_cidr to your trusted public IPv4 address with /32, for example 203.0.113.10/32."
  }
}

variable "public_key_path" {
  description = "Path to the public half of an SSH key pair already created locally. Terraform never reads or uploads the private key."
  type        = string
}

variable "project_name" {
  description = "Prefix used to name AWS resources."
  type        = string
  default     = "travel-expenses"
}
