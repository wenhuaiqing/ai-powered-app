# GitHub Actions -> Azure via workload identity federation.
# Same story as the AWS OIDC role: CI holds NO static cloud credentials.
# A user-assigned managed identity trusts tokens from this repo's main
# branch; azure/login exchanges the Actions OIDC token for ARM access.

resource "azurerm_user_assigned_identity" "gha" {
  name                = "id-${var.prefix}-gha"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_federated_identity_credential" "gha_main" {
  name                = "github-main"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.gha.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${var.github_repo}:ref:refs/heads/main"
}

# Contributor on the resource group: enough to `az containerapp update`.
resource "azurerm_role_assignment" "gha_rg_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.gha.principal_id
}
