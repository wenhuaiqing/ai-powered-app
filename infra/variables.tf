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
  description = "Full ECR image URI for the backend (used by the seed ECS task). Empty until the first GitHub Actions deploy pushes an image."
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repo (e.g. owenwen/ai-powered-app) allowed to assume the deploy role via OIDC."
  type        = string
  default     = "owenwen/ai-powered-app"
}

# Sensitive runtime secrets. Pass via `-var` or terraform.tfvars (which
# is gitignored). Each lands in Secrets Manager; the ECS task pulls them
# at start time.
variable "tavily_api_key" {
  description = "Tavily web search API key. Required for Market Watch + Compliance web fallback."
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key. Used for query-time embeddings (RAG retrievers) regardless of LLM_PROVIDER."
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL (e.g. https://<resource>.openai.azure.com/openai/v1/)."
  type        = string
  default     = ""
}

variable "azure_openai_embed_model" {
  description = "Azure OpenAI embedding deployment name."
  type        = string
  default     = "text-embedding-3-small"
}

locals {
  name = "${var.project}-${var.env}"
}
