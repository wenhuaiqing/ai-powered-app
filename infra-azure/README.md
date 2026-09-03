# Azure deployment - runbook

Terraform for the Azure topology (Container Apps + Azure OpenAI + MySQL
Flexible + Blob + Key Vault + workload identity federation). Design
rule: **AUD 0/month** after the $200 trial credits - scale-to-zero
apps, 12-month free MySQL B1ms, free blob tier, GHCR images, and chat on
Gemini's free tier. Azure OpenAI is kept for embeddings only (a query
embedding is ~40 tokens, so it rounds to 0.00 on the invoice).

```
Internet -> frontend (ACA, public, managed TLS)
              | nginx same-origin proxy (/api, /orb, /health)
              v
            backend (ACA, INTERNAL ingress only)
              |-- Azure OpenAI (gpt-4.1-mini + text-embedding-3-small,
              |     consumed via the OpenAI-compatible /openai/v1 surface)
              |-- MySQL Flexible B1ms (free 12mo)  [OLTP]
              |-- DuckDB (rebuilt from MySQL on boot) [OLAP]
              |-- Blob (public-read artefacts: model.pkl + parquets)
              +-- Key Vault via managed identity (Tavily, LLM key, MySQL pw,
                    write token)

Security posture: TLS verified to MySQL (least-privilege `app` login),
artefacts pinned by SHA-256 in artefacts.sha256, orb endpoints rate
limited + size capped, writes gated on the demo write token, CSP/HSTS
from nginx.
```

NOTE: the trial subscription allows exactly ONE Azure OpenAI account
(OpenAI.S0.AccountCount = 1). Terraform creates it - don't create
another by hand or the apply will fail on quota.

## Prerequisites (one-time)

1. **Azure CLI** + `az login` under the PERSONAL account. This machine
   keeps work/personal separate via `AZURE_CONFIG_DIR`:
   `$env:AZURE_CONFIG_DIR = "$env:USERPROFILE\.azure-personal"` before
   any az/terraform command for this project.
2. **Terraform** >= 1.7 (`winget install Hashicorp.Terraform`).
3. `infra-azure/terraform.tfvars` (gitignored) with
   `tavily_api_key = "..."` and `gemini_api_key = "..."` - the latter is
   a Google AI Studio key (aistudio.google.com/apikey) and is what keeps
   the LLM bill at zero. Omit it and chat falls back to Azure OpenAI at
   ~AUD 1-3/month. It must stay in tfvars: a bare `terraform apply`
   without it reverts chat to Azure OpenAI.
   (gitignored; generated from .env). No other secret input - the LLM
   key is created by Terraform and wired into Key Vault directly.

## Order of operations

### 1. Images on GHCR

`git push origin main` triggers `.github/workflows/deploy-azure.yml`;
the build-and-push job publishes `backend` + `frontend` images. Then
make both packages PUBLIC (one-time, web UI): github.com -> profile ->
Packages -> each package -> Package settings -> Change visibility ->
Public. ACA pulls them anonymously.

### 2. Terraform apply

```powershell
$env:AZURE_CONFIG_DIR = "$env:USERPROFILE\.azure-personal"
cd infra-azure
terraform init
terraform apply    # ~15 min; MySQL Flexible is the slow one
```

### 3. Point local .env at the new Azure OpenAI (for corpus builds)

```powershell
"LLM_BASE_URL=$(terraform output -raw llm_base_url)"   >> ..\.env
"LLM_API_KEY=$(terraform output -raw llm_api_key)"     >> ..\.env
```

### 4. Rebuild the RAG parquets (embedding model changed)

Titan v2 (1024-D) corpus vectors don't match text-embedding-3-small
(1536-D) queries - rebuild locally:

```powershell
cd ..\backend
uv run --python 3.12 python ..\scripts\build_regulation_corpus.py
uv run --python 3.12 python ..\scripts\build_review_embeddings.py
```

### 5. Upload artefacts to the blob container

```powershell
az storage blob upload-batch `
  --account-name $(terraform -chdir=..\infra-azure output -raw storage_account_name) `
  --destination artefacts --source ..\data `
  --pattern "model.pkl" --pattern "*.json" `
  --pattern "reviews_embeddings.parquet" `
  --pattern "regulations/embeddings.parquet"

# Pin what you just uploaded. The backend refuses to boot on a mismatch.
uv run python ..\scripts\hash_artefacts.py
git add ..\infra-azurertefacts.sha256
```

### 6. Seed MySQL (one-off, from this machine)

```powershell
# open the firewall for your IP:
terraform apply -var "seed_client_ip=<your public ip>"

$env:MYSQL_HOST     = terraform -chdir=..\infra-azure output -raw mysql_fqdn
$env:MYSQL_USER     = "appadmin"
$env:MYSQL_PASSWORD = terraform -chdir=..\infra-azure output -raw mysql_password
$env:MYSQL_DATABASE = "reapit_demo"
uv run --python 3.12 python ..\scripts\seed_all.py

# Least-privilege login the app runs as (SELECT *, UPDATE leads, INSERT
# lead_events/agent_runs). Re-run whenever mysql_app_password rotates.
$env:MYSQL_SSL          = "true"
$env:MYSQL_APP_PASSWORD = terraform -chdir=..\infra-azure output -raw mysql_app_password
uv run --python 3.12 python ..\scripts\create_app_user.py

# then close the firewall again:
terraform apply
```

Schema changes later on: `uv run python ..\scripts\migrate_mysql.py` with
the same admin env (open the firewall first). The app user has no DDL
rights by design.

### 7. Wire CI (repo secrets, one-time)

From `terraform output`: `AZURE_CLIENT_ID` (= gha_client_id),
`AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` - the deploy workflow's
OIDC login. For the evals-smoke workflow: `LLM_BASE_URL`,
`LLM_API_KEY`, `TAVILY_API_KEY`. After this, every push to main
builds, pushes, and rolls both apps - no static cloud keys in CI.

### 8. Operator unlock (writes + trusted runs)

The public site is read-only and rate limited. To demo lead status
changes, bypass the limiter, and have your prompts shown verbatim on the
Dashboard feed, open the site once per browser session with the token:

```powershell
$token = terraform -chdir=infra-azure output -raw demo_write_token
Start-Process "$(terraform -chdir=infra-azure output -raw frontend_url)/?write_token=$token"
```

The frontend stores it in sessionStorage, scrubs it from the URL and
sends `X-Write-Token` on every call. Anonymous visitors' prompts appear in
the feed as generated labels ("Compliance check from Properties (L0055)").

### 9. Smoke it

```powershell
$url = terraform -chdir=infra-azure output -raw frontend_url
curl "$url/health"     # cold start ~20-40s on the first hit
cd backend
uv run --python 3.12 python ..\evals\run.py --tier smoke --backend $url
```

### 10. Afterwards

- Update the main README's demo-status block with the live URL.
- ~~Day 30~~ **PAYG upgrade done 03/09/2026.** Do it early, not on
  day 30: the credit stays usable for the full 30 days from signup, so
  upgrading early forfeits nothing and removes the deadline. Pick the
  free **Basic** support plan - Developer is ~$29/month.
- Budget `budget-aipapp-monthly` exists (AUD 10/month, alerts at
  50/80/100% actual + 100% forecast). Created with
  `az deployment sub create`, **not** Terraform - codify it here if this
  stack is rebuilt. PAYG has no hard spending cap; the budget only
  alerts.

## Known limits (by design)

- **Cold starts**: scale-to-zero means the first request after idle
  pays image pull + artefact download + DuckDB rebuild (~20-40s).
  Fine for a portfolio demo; the README says so honestly.
- **Container Apps free grant**: the never-expiring 180k vCPU-s +
  360k GiB-s covers 0.75 vCPU / 1.5 GiB of sidecars for **66 h of
  active replica time per month**. Both meters bind at the same point.
  Depends on `min_replicas = 0`; setting it to 1 is 730 h/month and
  leaves the grant entirely. Price it before flipping it.
- **MySQL free window**: B1ms is free for 12 months, then **AUD ~30/month**
  at australiaeast list (B1MS 0.0362/h = 26.43, plus 20 GB at
  0.1919/GB = 3.84) - roughly double the USD figure this file used to
  quote. Revisit before **Sep 2027**. Decided replacement: the **Azure
  SQL Database free offer** - 100k vCore-s + 32 GB per database per
  month for the *lifetime* of the subscription, and its default at the
  limit is auto-pause, not billing. Cost is a T-SQL dialect port
  (driver in `mysql_client.py`, `lastrowid` -> `SCOPE_IDENTITY()`,
  AUTO_INCREMENT/utf8mb4/ON UPDATE in `scripts/migrate_mysql.py`,
  `LIMIT` -> `OFFSET...FETCH`). Zero-code fallback: TiDB Cloud Starter,
  which is MySQL wire-compatible. Aiven's free MySQL is out - it reaps
  services left idle, which is exactly this demo's pattern.
- **Gemini free-tier limits**: chat runs on `gemini-3.5-flash` free
  tier. Google no longer publishes static limits (they are per-project,
  visible in AI Studio), but reported figures are ~15 RPM. The Property
  Matcher run fans valuation out across ~5 candidates, so it can reach
  12-15 calls in a minute - the closest thing to a ceiling here. A 429
  degrades to keyword routing rather than failing, but it will look
  worse in a live demo. Set `gemini_api_key = ""` to fall straight back
  to Azure OpenAI.
- **Model deprecation**: gpt-4.1-mini retires 2027-04. Swapping models
  is a config change (new azurerm_cognitive_deployment + env value).
