variable "prefix" {
  description = "Short resource-name prefix (lowercase alphanumerics)."
  type        = string
  default     = "aipapp"
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "australiaeast"
}

variable "github_repo" {
  description = "GitHub repo (owner/name) allowed to deploy via OIDC."
  type        = string
  default     = "wenhuaiqing/ai-powered-app"
}

variable "backend_image" {
  description = "Backend container image (public GHCR)."
  type        = string
  default     = "ghcr.io/wenhuaiqing/ai-powered-app/backend:latest"
}

variable "frontend_image" {
  description = "Frontend container image (public GHCR)."
  type        = string
  default     = "ghcr.io/wenhuaiqing/ai-powered-app/frontend:latest"
}

variable "tavily_api_key" {
  description = "Tavily web-search API key (stored in Key Vault)."
  type        = string
  sensitive   = true
}

variable "github_models_token" {
  description = "GitHub fine-grained PAT with `models: read` (stored in Key Vault)."
  type        = string
  sensitive   = true
}

variable "seed_client_ip" {
  description = "Optional: your public IP, to open MySQL for the one-off local seed run. Leave empty to keep MySQL Azure-only."
  type        = string
  default     = ""
}
