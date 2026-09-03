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

# Which endpoint serves chat. Deliberately NOT derived from whether
# gemini_api_key is set: Terraform propagates the key's sensitivity into
# every expression touching it, which would redact LLM_BASE_URL and
# LLM_CHAT_MODEL in plan output -- the two values most worth reading
# before an apply. Keeping the selector separate keeps the plan legible.
variable "chat_provider" {
  description = "Endpoint serving chat: \"gemini\" or \"azure\". Embeddings always stay on Azure OpenAI."
  type        = string
  default     = "gemini"

  validation {
    condition     = contains(["gemini", "azure"], var.chat_provider)
    error_message = "chat_provider must be \"gemini\" or \"azure\"."
  }
}

variable "gemini_api_key" {
  description = "Google AI Studio key. Required when chat_provider is \"gemini\"."
  type        = string
  sensitive   = true
  default     = ""
}

variable "gemini_chat_model" {
  description = "Gemini model id for chat. Use a Lite model: gemini-3.5-flash is capped at 5 requests/minute on the free tier, and one Orb run is 5-9 sequential LLM calls."
  type        = string
  default     = "gemini-3.5-flash-lite"
}

variable "seed_client_ip" {
  description = "Optional: your public IP, to open MySQL for the one-off local seed run. Leave empty to keep MySQL Azure-only."
  type        = string
  default     = ""
}
