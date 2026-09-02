resource "azurerm_resource_group" "main" {
  name     = "rg-${var.prefix}"
  location = var.location
}

# Log Analytics: Container Apps environment logging. PerGB2018 includes
# 5 GB/month free ingestion - a scale-to-zero demo won't dent it.
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}
