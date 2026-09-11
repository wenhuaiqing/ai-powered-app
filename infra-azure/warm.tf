# Scheduled warm pings for the demo - one Container Apps cron Job per
# window rather than a GitHub Actions schedule. GitHub's cron is
# best-effort ("delayed or skipped during periods of high load") and on
# 11/09/2026 it fired zero of four morning pings, leaving a viewer to pay a
# ~100 s scale-from-zero at 11:13 AEST. These run on the environment's
# Kubernetes CronJob scheduler, to the second.
#
# Windows (AEST, weekdays; Brisbane has no daylight saving, so UTC is a
# fixed -10):
#   10:00-11:30  pings 00:00, 00:20, 00:40, 01:00 UTC
#   14:00-15:00  pings 04:00, 04:20, 04:30 UTC
# Each ping is an ordinary request through ingress and resets the app's
# 30-minute scale-to-zero cooldown. Pings are 20 minutes apart so a late
# fire cannot open a 30-minute gap; the last ping in each window sits 30
# minutes before the window ends, so the cooldown finishes at the boundary.
# Alive time ~2.5 h/weekday, ~55 h/month, inside the ~66.7 h free grant at
# the app's 0.75 vCPU. Each job execution is a curl for a few seconds at
# 0.25 vCPU - a few hundred vCPU-seconds a month from the same grant.
#
# Kubernetes cron holds one expression, so three jobs. On-demand warming
# stays in .github/workflows/warm.yml (workflow_dispatch only).
#
# Execution history:
#   az containerapp job execution list -n job-warm-am -g rg-aipapp -o table

locals {
  warm_schedules = {
    am      = "0,20,40 0 * * 1-5" # 10:00, 10:20, 10:40 AEST
    am-last = "0 1 * * 1-5"       # 11:00 AEST -> cooldown ends 11:30
    pm      = "0,20,30 4 * * 1-5" # 14:00, 14:20, 14:30 AEST -> cooldown ends 15:00
  }
  warm_url = "https://${azurerm_container_app.app.ingress[0].fqdn}/health"
}

resource "azurerm_container_app_job" "warm" {
  for_each = local.warm_schedules

  name                         = "job-warm-${each.key}"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  workload_profile_name        = "Consumption"

  # The platform holds a cold-start request for up to ~4 minutes; give curl
  # room to wait through one, then stop. No platform retries: curl retries
  # itself, and a Failed execution is the signal worth seeing.
  replica_timeout_in_seconds = 300
  replica_retry_limit        = 0

  schedule_trigger_config {
    cron_expression          = each.value
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "curl"
      image   = "docker.io/curlimages/curl:8.10.1"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["curl"]
      # %%{ is Terraform's escape for a literal %{ - these are curl's
      # --write-out variables, not template directives.
      args = [
        "-fsS",
        "--max-time", "240",
        "--retry", "2",
        "--retry-all-errors",
        "--retry-delay", "10",
        "-o", "/dev/null",
        "-w", "warm ping: HTTP %%{http_code} in %%{time_total}s\n",
        local.warm_url,
      ]
    }
  }
}
