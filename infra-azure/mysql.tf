# OLTP database - Azure Database for MySQL Flexible Server.
# B_Standard_B1ms + 20 GB sits inside the Azure free account's
# 12-month free allowance (750 h/month B1ms + 32 GB storage).

resource "random_password" "mysql" {
  length  = 24
  special = false # keep it URL/connection-string safe
}

resource "azurerm_mysql_flexible_server" "main" {
  name                   = "mysql-${var.prefix}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  administrator_login    = "appadmin"
  administrator_password = random_password.mysql.result
  sku_name               = "B_Standard_B1ms"
  version                = "8.0.21"

  storage {
    size_gb           = 20
    auto_grow_enabled = false
  }

  # Public access + firewall rules (no VNet: ACA consumption-plan apps
  # egress over public internet; TLS is enforced by the server).
  zone = "1"
}

resource "azurerm_mysql_flexible_database" "app" {
  name                = "reapit_demo"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_mysql_flexible_server.main.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# Allow Azure-internal services (the Container Apps) to reach MySQL.
resource "azurerm_mysql_flexible_server_firewall_rule" "azure_services" {
  name                = "allow-azure-services"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_mysql_flexible_server.main.name
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
}

# Optional: open your own IP for the one-off seed run from the laptop.
resource "azurerm_mysql_flexible_server_firewall_rule" "seed_client" {
  count               = var.seed_client_ip == "" ? 0 : 1
  name                = "allow-seed-client"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_mysql_flexible_server.main.name
  start_ip_address    = var.seed_client_ip
  end_ip_address      = var.seed_client_ip
}

# PyMySQL connects without explicit TLS parameters, and Azure MySQL
# defaults to require_secure_transport=ON, which would reject it.
# The data is public Kaggle derivatives on a demo, so the pragmatic
# call is to relax the requirement rather than thread TLS options
# through the connection string.
resource "azurerm_mysql_flexible_server_configuration" "no_tls_requirement" {
  name                = "require_secure_transport"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_mysql_flexible_server.main.name
  value               = "OFF"
}
