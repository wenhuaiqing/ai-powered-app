output "frontend_url" {
  description = "The public demo URL (managed TLS included)."
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}

output "artefact_base_url" {
  description = "Public-read blob base URL for model + parquet artefacts."
  value       = "${azurerm_storage_account.artefacts.primary_blob_endpoint}${azurerm_storage_container.artefacts.name}"
}

output "storage_account_name" {
  value = azurerm_storage_account.artefacts.name
}

output "mysql_fqdn" {
  value = azurerm_mysql_flexible_server.main.fqdn
}

output "mysql_admin_login" {
  value = azurerm_mysql_flexible_server.main.administrator_login
}

output "mysql_password" {
  value     = random_password.mysql.result
  sensitive = true
}

output "mysql_app_password" {
  description = "Password for the least-privilege 'app' login (feed to scripts/create_app_user.py)."
  value       = random_password.mysql_app.result
  sensitive   = true
}

output "demo_write_token" {
  description = "Unlock writes + trusted runs in a browser: <frontend_url>/?write_token=<this>."
  value       = random_password.demo_write_token.result
  sensitive   = true
}

# Values for GitHub repo secrets (deploy workflow's azure/login):
output "gha_client_id" {
  description = "Set as repo secret AZURE_CLIENT_ID."
  value       = azurerm_user_assigned_identity.gha.client_id
}

output "tenant_id" {
  description = "Set as repo secret AZURE_TENANT_ID."
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Set as repo secret AZURE_SUBSCRIPTION_ID."
  value       = data.azurerm_client_config.current.subscription_id
}

output "llm_base_url" {
  description = "OpenAI-compatible base URL (for local .env during corpus builds)."
  value       = "${azurerm_cognitive_account.openai.endpoint}openai/v1/"
}

output "llm_api_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}
