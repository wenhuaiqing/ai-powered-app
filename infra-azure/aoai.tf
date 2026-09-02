# Azure OpenAI - the demo's LLM + embedding provider.
#
# The trial subscription allows exactly ONE OpenAI account
# (OpenAI.S0.AccountCount = 1) - this is it. The backend consumes it
# through the OpenAI-compatible /openai/v1 surface, so the app code is
# provider-neutral (see backend services/openai_chat.py).
#
# Quota reality on the free subscription (checked 2026-08):
#   gpt-4.1-mini      GlobalStandard  200K TPM available -> we take 50
#   text-embedding-3-small  Standard  350K TPM available -> we take 50

resource "azurerm_cognitive_account" "openai" {
  name                  = "aoai-${var.prefix}-${random_string.storage_suffix.result}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "aoai-${var.prefix}-${random_string.storage_suffix.result}"
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = "gpt-4-1-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4.1-mini"
    version = "2025-04-14"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 50
  }
}

resource "azurerm_cognitive_deployment" "embed" {
  name                 = "text-embedding-3-small"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }

  sku {
    name     = "Standard"
    capacity = 50
  }

  # Serialise deployments - the account rejects concurrent changes.
  depends_on = [azurerm_cognitive_deployment.chat]
}
