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

variable "gemini_api_key" {
  description = "Google AI Studio key. Chat runs on Gemini's free tier so the demo bills nothing; leave empty to keep chat on Azure OpenAI."
  type        = string
  sensitive   = true
  default     = ""
}

variable "gemini_chat_model" {
  description = "Gemini model id for chat. Free tier: gemini-3.5-flash (best quality) or gemini-3.5-flash-lite (higher daily quota)."
  type        = string
  default     = "gemini-3.5-flash"
}

variable "seed_client_ip" {
  description = "Optional: your public IP, to open MySQL for the one-off local seed run. Leave empty to keep MySQL Azure-only."
  type        = string
  default     = ""
}
