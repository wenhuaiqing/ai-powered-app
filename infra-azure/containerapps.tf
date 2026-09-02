# Container Apps: consumption plan, scale-to-zero.
#
# Topology mirrors the AWS design one abstraction level up:
#   - frontend: PUBLIC ingress (the only public URL; free managed TLS).
#     nginx serves the SPA and proxies /api, /orb, /health to the
#     backend over the environment's internal DNS -- same-origin, so
#     no CORS anywhere.
#   - backend: INTERNAL ingress only -- unreachable from the internet,
#     the ACA analogue of the AWS private subnet.
# Secrets come from Key Vault via a user-assigned managed identity --
# nothing sensitive in app config or images ("keys nowhere").

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${var.prefix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

# ---- identity + Key Vault -------------------------------------------

resource "azurerm_user_assigned_identity" "backend" {
  name                = "id-${var.prefix}-backend"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                      = "kv-${var.prefix}-${random_string.storage_suffix.result}"
  location                  = azurerm_resource_group.main.location
  resource_group_name       = azurerm_resource_group.main.name
  tenant_id                 = data.azurerm_client_config.current.tenant_id
  sku_name                  = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled  = false
}

# Terraform (the operator) writes secrets.
resource "azurerm_role_assignment" "kv_admin_self" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# The backend's identity reads them.
resource "azurerm_role_assignment" "kv_backend_read" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.backend.principal_id
}

resource "azurerm_key_vault_secret" "tavily" {
  name         = "tavily-api-key"
  value        = var.tavily_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin_self]
}

resource "azurerm_key_vault_secret" "llm_api_key" {
  name         = "llm-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin_self]
}

resource "azurerm_key_vault_secret" "mysql_password" {
  name         = "mysql-password"
  value        = random_password.mysql.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin_self]
}

# ---- the app: nginx + backend as sidecars in ONE container app ------
#
# Originally two apps (frontend public, backend internal). The
# environment's internal ingress pool proved flaky under revision churn
# (a stale Envoy pod black-holing ~1 in 7 connections), so the backend
# now rides in the same replica and nginx proxies to 127.0.0.1:8000 -
# no internal ingress, no second Envoy, one activation on cold start.

resource "azurerm_container_app" "app" {
  name                         = "app"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.backend.id]
  }

  ingress {
    external_enabled = true
    target_port      = 80 # nginx
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  secret {
    name                = "tavily-api-key"
    key_vault_secret_id = azurerm_key_vault_secret.tavily.id
    identity            = azurerm_user_assigned_identity.backend.id
  }
  secret {
    name                = "llm-api-key"
    key_vault_secret_id = azurerm_key_vault_secret.llm_api_key.id
    identity            = azurerm_user_assigned_identity.backend.id
  }
  secret {
    name                = "mysql-password"
    key_vault_secret_id = azurerm_key_vault_secret.mysql_password.id
    identity            = azurerm_user_assigned_identity.backend.id
  }

  template {
    min_replicas = 0 # scale to zero: the whole point
    max_replicas = 1

    container {
      name   = "frontend"
      image  = var.frontend_image
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "BACKEND_UPSTREAM"
        value = "127.0.0.1:8000"
      }
    }

    container {
      name   = "backend"
      image  = var.backend_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "ARTEFACT_BASE_URL"
        value = "${azurerm_storage_account.artefacts.primary_blob_endpoint}${azurerm_storage_container.artefacts.name}"
      }
      env {
        name  = "LLM_BASE_URL"
        value = "${azurerm_cognitive_account.openai.endpoint}openai/v1/"
      }
      env {
        name        = "LLM_API_KEY"
        secret_name = "llm-api-key"
      }
      env {
        name  = "LLM_CHAT_MODEL"
        value = azurerm_cognitive_deployment.chat.name
      }
      env {
        name  = "LLM_EMBED_MODEL"
        value = azurerm_cognitive_deployment.embed.name
      }
      env {
        name  = "MYSQL_HOST"
        value = azurerm_mysql_flexible_server.main.fqdn
      }
      env {
        name  = "MYSQL_USER"
        value = azurerm_mysql_flexible_server.main.administrator_login
      }
      env {
        name        = "MYSQL_PASSWORD"
        secret_name = "mysql-password"
      }
      env {
        name  = "MYSQL_DATABASE"
        value = azurerm_mysql_flexible_database.app.name
      }
    }
  }
}
