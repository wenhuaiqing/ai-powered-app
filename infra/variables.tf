variable "region" {
  description = "AWS region. ap-southeast-2 (Sydney) for the demo narrative."
  type        = string
  default     = "ap-southeast-2"
}

variable "env" {
  description = "Environment name (dev / staging / prod). Used as a name suffix."
  type        = string
  default     = "demo"
}

variable "project" {
  description = "Project name prefix for resources."
  type        = string
  default     = "ai-powered-app"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "azs" {
  description = "Two AZs in the chosen region. AWS picks the names per region."
  type        = list(string)
  default     = ["ap-southeast-2a", "ap-southeast-2b"]
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.40.0.0/24", "10.40.1.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.40.10.0/24", "10.40.11.0/24"]
}

variable "db_instance_class" {
  description = "RDS instance class. db.t4g.micro is the cheapest current-gen."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage_gb" {
  type    = number
  default = 20
}

variable "db_name" {
  type    = string
  default = "reapit_demo"
}

variable "db_username" {
  type    = string
  default = "app"
}

variable "db_engine_version" {
  type    = string
  default = "8.0"
}

variable "seed_image_uri" {
  description = "Full ECR image URI for the backend (used by the seed ECS task). Empty until Phase 2 step 2 publishes the image."
  type        = string
  default     = ""
}

locals {
  name = "${var.project}-${var.env}"
}
