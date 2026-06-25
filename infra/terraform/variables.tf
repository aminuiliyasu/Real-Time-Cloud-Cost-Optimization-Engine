variable "project_name" {
  description = "Project name used for tagging resources."
  type        = string
  default     = "rtcco"
}

variable "aws_region" {
  description = "AWS region for infrastructure resources."
  type        = string
  default     = "eu-central-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name used by Terraform."
  type        = string
  default     = "default"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet."
  type        = string
  default     = "10.20.1.0/24"
}

variable "instance_type" {
  description = "EC2 instance type for backend host."
  type        = string
  default     = "t3.small"
}

variable "ami_id" {
  description = "Optional custom AMI ID. Leave empty to use latest Amazon Linux 2023."
  type        = string
  default     = ""
}

variable "ssh_cidr" {
  description = "CIDR allowed to access instance over SSH."
  type        = string
  default     = "0.0.0.0/0"
}
