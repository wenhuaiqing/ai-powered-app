# Artefact store: model.pkl + RAG embedding parquets, downloaded by the
# backend on boot over plain HTTPS. The container is PUBLIC READ by
# design - the artefacts are derived from public Kaggle data, and a
# public blob means the cold-start path has no SDK, no credential, and
# no identity dependency that could fail.

resource "random_string" "storage_suffix" {
  length  = 6
  lower   = true
  upper   = false
  special = false
}

resource "azurerm_storage_account" "artefacts" {
  name                     = "st${var.prefix}${random_string.storage_suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Required for a public-read container.
  allow_nested_items_to_be_public = true
}

resource "azurerm_storage_container" "artefacts" {
  name                  = "artefacts"
  storage_account_id    = azurerm_storage_account.artefacts.id
  container_access_type = "blob" # anonymous read on blobs, no listing
}
