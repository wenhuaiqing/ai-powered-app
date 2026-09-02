# Azure deployment - Terraform skeleton.
#
# Design rule: the whole topology must cost ~$0/month AFTER the $200
# trial credits, so the demo survives on the free tier indefinitely:
#   - Container Apps consumption plan, scale-to-zero (always-free grant)
#   - MySQL Flexible Server B1ms (750 h/month free for 12 months)
#   - Storage account for artefacts (5 GB free for 12 months)
#   - Key Vault + managed identity for secrets (pennies)
#   - Images on GHCR (free), CI auth via workload identity federation
#
# State is local (single dev machine, portfolio project) - same call as
# the AWS infra/.

terraform {
  required_version = ">= 1.7"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
}
