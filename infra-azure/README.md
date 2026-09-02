# Azure deployment - runbook

Terraform for the Azure topology (Container Apps + MySQL Flexible +
Blob + Key Vault + workload identity federation). Design rule: ~$0/month
after the $200 trial credits - scale-to-zero apps, 12-month free MySQL
B1ms, free blob tier, GHCR images, GitHub Models free LLM tier.

```
Internet -> frontend (ACA, public, managed TLS)
              | nginx same-origin proxy (/api, /orb, /health)
              v
            backend (ACA, INTERNAL ingress only)
              |-- MySQL Flexible B1ms (free 12mo)  [OLTP]
              |-- DuckDB (rebuilt from MySQL on boot) [OLAP]
              |-- Blob (public-read artefacts: model.pkl + parquets)
              |-- Key Vault via managed identity (Tavily, PAT, MySQL pw)
              +-- GitHub Models (chat + embeddings, free tier)
```

## Prerequisites (one-time)

1. **Azure CLI**: `winget install Microsoft.AzureCLI`, then `az login`.
2. **Terraform**: `winget install Hashicorp.Terraform` (or any >= 1.7).
3. **GitHub fine-grained PAT** with the **Models: read** permission
   (github.com -> Settings -> Developer settings -> Fine-grained tokens).
   This is the runtime LLM credential on Azure. CI needs no PAT - the
   workflow's built-in GITHUB_TOKEN calls GitHub Models.
4. Tavily API key (same one as before).

## Order of operations

### 1. Rebuild the RAG parquets (embedding model changed)

Titan v2 (1024-D) corpus vectors don't match text-embedding-3-small
(1536-D) queries - rebuild locally before uploading:

```powershell
# backend/.env: add
#   GITHUB_MODELS_TOKEN=<your PAT>
cd backend
uv run --python 3.12 python ../scripts/build_regulation_corpus.py
uv run --python 3.12 python ../scripts/build_review_embeddings.py
```

(If `data/` is empty first run `build_db.py` + `train_model.py` per the
main README.)

### 2. Push images to GHCR (bootstrap - before first apply)

The container apps reference GHCR images, so they must exist first:

```powershell
git push origin main          # also publishes the honest README
gh workflow run deploy-azure.yml
```

The build-and-push job succeeds; the deploy job FAILS on this first run
(no Azure secrets yet) - expected. Then make both packages public so
ACA can pull anonymously: github.com -> your profile -> Packages ->
`ai-powered-app/backend` + `/frontend` -> Package settings ->
Change visibility -> Public.

### 3. Terraform apply

```powershell
cd infra-azure
terraform init
terraform apply `
  -var "tavily_api_key=<tavily key>" `
  -var "github_models_token=<PAT>"
```

(~10-15 min; MySQL Flexible is the slow one.)

### 4. Upload artefacts to the blob container

```powershell
az storage blob upload-batch `
  --account-name $(terraform output -raw storage_account_name) `
  --destination artefacts `
  --source ../data `
  --pattern "model.pkl" --pattern "*.json" `
  --pattern "reviews_embeddings.parquet" `
  --pattern "regulations/embeddings.parquet"
```

### 5. Seed MySQL (one-off, from this machine)

```powershell
# open the firewall for your IP:
terraform apply -var "seed_client_ip=$( (Invoke-WebRequest ifconfig.me/ip).Content.Trim() )" ...same vars...

cd ..\backend
$env:MYSQL_HOST     = terraform -chdir=..\infra-azure output -raw mysql_fqdn
$env:MYSQL_USER     = "appadmin"
$env:MYSQL_PASSWORD = terraform -chdir=..\infra-azure output -raw mysql_password
$env:MYSQL_DATABASE = "reapit_demo"
uv run --python 3.12 python ..\scripts\seed_all.py
```

Then re-apply without `seed_client_ip` to close the firewall again.

### 6. Wire CI/CD (repo secrets)

From `terraform output`: create GitHub repo secrets
`AZURE_CLIENT_ID` (= gha_client_id), `AZURE_TENANT_ID`,
`AZURE_SUBSCRIPTION_ID`. Every push to main now builds, pushes, and
rolls both apps - no static cloud keys anywhere.

### 7. Smoke it

```powershell
$url = terraform -chdir=infra-azure output -raw frontend_url
curl "$url/health"                     # expect {"status":"ok"} (cold start ~20-40s first hit)
cd backend
uv run --python 3.12 python ..\evals\run.py --tier smoke --backend $url
```

### 8. Afterwards

- Update the main README's demo-status block with the live URL.
- **Day 30**: upgrade the subscription to pay-as-you-go (Portal banner)
  or Azure stops the services when trial credits lapse. With this
  design the ongoing bill is ~$0-3/month.
- Optional: `az consumption budget` alert at $10/month for peace of mind.

## Known limits (by design)

- **Cold starts**: scale-to-zero means the first request after idle
  pays image pull + artefact download + DuckDB rebuild (~20-40s).
  Fine for a portfolio demo; the README can say so honestly.
- **GitHub Models free tier**: per-minute + per-day caps (gpt-4o-mini
  tier). A multi-agent run is 3-6 calls; budget ~25-40 demo prompts/day.
  On a 429 the planner's heuristic fallback keeps the demo functional -
  graceful degradation doing its job.
- **MySQL free window**: B1ms is free for 12 months on a free account,
  then ~$15-20/month - revisit before Aug 2027.
