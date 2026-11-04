variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name identifier"
  type        = string
  default     = "zestora"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the custom VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_1_cidr" {
  description = "CIDR block for Public Subnet 1 (AZ a)"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_2_cidr" {
  description = "CIDR block for Public Subnet 2 (AZ b)"
  type        = string
  default     = "10.0.2.0/24"
}

variable "instance_type" {
  description = "EC2 instance type (t3.micro / t2.micro is Free Tier eligible)"
  type        = string
  default     = "t3.micro"
}

variable "ssh_key_name" {
  description = "Name of the existing AWS Key Pair to attach for SSH access"
  type        = string
  default     = ""
}

variable "admin_ip_cidr" {
  description = "Allowed CIDR block for SSH access (default is open, recommend your IP/32)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in GB (Free tier covers up to 30GB)"
  type        = number
  default     = 20
}
