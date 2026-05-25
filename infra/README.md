# infra/

Terraform for the ai-powered-app AWS footprint. Phase 2 step 0 landed
the data layer; **step 3** (this expansion) adds compute (ECS Fargate +
ALB + ECR) and **step 4** wires GitHub Actions OIDC for hands-free
deploys.

## What's here

| File | What it provisions |
|---|---|
| `versions.tf`     | Terraform + AWS provider pins |
| `variables.tf`    | region, env, instance sizing, GitHub repo identifier |
| `network.tf`      | VPC (2 AZs), public + private subnets, IGW, NAT Gateway, route tables, app SG |
| `rds.tf`          | `aws_db_subnet_group` + security group + `db.t4g.micro` MySQL 8 in private subnets |
| `secrets.tf`      | `random_password` -> `aws_secretsmanager_secret` (the app reads it via the task role) |
| `iam.tf`          | ECS task execution + task roles |
| `ecr.tf`          | Two ECR repos with `keep-last-10` lifecycle policies |
| `alb.tf`          | Single ALB (public subnets) + 2 target groups + listener rules: `/api/*` `/orb/*` `/health` -> backend, everything else -> frontend |
| `ecs_services.tf` | Backend + frontend task defs + Fargate services (private subnets), CloudWatch log groups, Bedrock invoke policy on the task role |
| `github_oidc.tf`  | GitHub OIDC provider + scoped deploy role (no static AWS keys in GitHub) |
| `seed_task.tf`    | One-shot ECS task definition that runs `scripts/seed_all.py` against RDS once an image lands in ECR |
| `outputs.tf`      | ALB DNS, ECR URIs, ECS service / family names, deploy role ARN |

## What's deliberately omitted

- **HTTPS / ACM cert / custom domain** — adds $15/yr + DNS setup. Trivial
  to bolt on; the listener becomes 80->443 redirect + a 443 listener.
- **Autoscaling, multi-AZ RDS, WAF** — overkill for a portfolio demo.
- **VPC endpoints for Bedrock + Secrets Manager** — Bedrock would save a
  NAT round-trip; deferred since traffic is tiny.

## First apply (one-time)

1. **Enable Bedrock access** in the AWS console (one-time click per model):
   - `anthropic.claude-sonnet-4-6-20250930-v1:0` for chat
   - Region must match `var.region` (default `ap-southeast-2`)
2. **Configure AWS CLI** locally: `aws configure` with an admin or
   close-to-admin user, or `aws sso login` if using SSO.
3. **Set `github_repository`** in `variables.tf` (or pass via
   `-var "github_repository=owner/repo"`).
4. Apply:

```bash
cd infra
terraform init
terraform plan       # review -- creates ~35 resources
terraform apply
```

~10 minutes total (RDS provisioning is the slow part). When done, the
ECS services try to start but fail because no image has been pushed
yet -- expected. The first GitHub Actions deploy fixes that.

## Wire GitHub Actions (one-time)

After `terraform apply`, copy the outputs into the repo's
**Settings -> Secrets and variables -> Actions -> Variables** tab:

```bash
terraform output -raw github_actions_role_arn       # -> AWS_DEPLOY_ROLE_ARN
terraform output -raw region                        # -> AWS_REGION
terraform output -raw ecr_backend_repository_url    # split: registry / repo path
terraform output -raw ecr_frontend_repository_url   # ditto
terraform output -raw ecs_cluster_name              # -> ECS_CLUSTER
terraform output -raw ecs_backend_service_name      # -> ECS_BACKEND_SERVICE
terraform output -raw ecs_frontend_service_name     # -> ECS_FRONTEND_SERVICE
terraform output -raw ecs_backend_task_family       # -> ECS_BACKEND_TASK_FAMILY
terraform output -raw ecs_frontend_task_family      # -> ECS_FRONTEND_TASK_FAMILY
```

The `ECR_BACKEND_REPOSITORY` / `ECR_FRONTEND_REPOSITORY` variables hold
only the repo *path* portion (e.g. `ai-powered-app-demo/backend`) -- the
registry hostname is derived from the ECR login output inside the
workflow.

## Seed RDS the first time

The seed task definition can run once an image is in ECR:

```bash
aws ecs run-task \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --task-definition $(terraform output -raw seed_task_family) \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
      subnets=[$(terraform output -raw private_subnet_id_a)],
      securityGroups=[$(terraform output -raw app_security_group_id)],
      assignPublicIp=DISABLED}"
```

Logs in `/aws/ecs/ai-powered-app-demo/seed`. Run again any time the
source CSVs change.

## App URL

```bash
echo "http://$(terraform output -raw alb_dns_name)"
```

## ALB access logs + Athena

Every HTTP request hitting the ALB lands in S3 (gzipped, partitioned by
`AWSLogs/<account>/elasticloadbalancing/<region>/YYYY/MM/DD/`). Useful
for:

- Confirming a recruiter clicked the live demo URL (IP geolocation +
  user agent + timestamp)
- Debugging 5xx spikes after a deploy
- Auditing what paths are getting hit (post-launch SEO-style insight)

Bucket name lives in the Terraform output:

```bash
terraform output -raw s3_alb_logs_bucket
# e.g. ai-powered-app-demo-alb-logs-766265104419
```

Logs start landing ~5 minutes after `terraform apply` enables them.

### One-time Athena setup

Open **AWS Console → Athena → Query editor**. If this is your first
time, set a query result location (any bucket; create a fresh
`ai-powered-app-demo-athena-results-<account>` if needed).

Then run this CREATE TABLE once — substitute `<bucket>` with the value
from `terraform output -raw s3_alb_logs_bucket` and `<account>` with
your AWS account ID:

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS alb_logs (
    type                            string,
    time                            string,
    elb                             string,
    client_ip                       string,
    client_port                     int,
    target_ip                       string,
    target_port                     int,
    request_processing_time         double,
    target_processing_time          double,
    response_processing_time        double,
    elb_status_code                 int,
    target_status_code              string,
    received_bytes                  bigint,
    sent_bytes                      bigint,
    request_verb                    string,
    request_url                     string,
    request_proto                   string,
    user_agent                      string,
    ssl_cipher                      string,
    ssl_protocol                    string,
    target_group_arn                string,
    trace_id                        string,
    domain_name                     string,
    chosen_cert_arn                 string,
    matched_rule_priority           string,
    request_creation_time           string,
    actions_executed                string,
    redirect_url                    string,
    lambda_error_reason             string,
    target_port_list                string,
    target_status_code_list         string,
    classification                  string,
    classification_reason           string,
    conn_trace_id                   string
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
    'serialization.format' = '1',
    'input.regex' =
    '([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) \\\"([^ ]*) (.*) (- |[^ ]*)\\\" \\\"([^\\\"]*)\\\" ([A-Z0-9-_]+) ([A-Za-z0-9.-]*) ([^ ]*) \\\"([^\\\"]*)\\\" \\\"([^\\\"]*)\\\" \\\"([^\\\"]*)\\\" ([-.0-9]*) ([^ ]*) \\\"([^\\\"]*)\\\" \\\"([^\\\"]*)\\\" \\\"([^ ]*)\\\" \\\"([^\\s]+?)\\\" \\\"([^\\s]+)\\\" \\\"([^ ]*)\\\" \\\"([^ ]*)\\\" ?([^ ]*)?'
)
LOCATION 's3://<bucket>/AWSLogs/<account>/elasticloadbalancing/ap-southeast-2/';
```

This points Athena at the bucket; logs become queryable immediately.

### Useful queries

**Who visited the live URL in the last 24h?**

```sql
SELECT
    from_iso8601_timestamp(time) AS request_time,
    client_ip,
    request_url,
    elb_status_code,
    user_agent
FROM alb_logs
WHERE from_iso8601_timestamp(time) > current_timestamp - interval '1' day
  AND request_url LIKE '%/' OR request_url LIKE '%/dashboard%'
ORDER BY request_time DESC
LIMIT 100;
```

**Unique visitors (by IP) per day**:

```sql
SELECT
    date(from_iso8601_timestamp(time)) AS day,
    COUNT(DISTINCT client_ip) AS unique_ips,
    COUNT(*) AS total_requests
FROM alb_logs
GROUP BY 1
ORDER BY 1 DESC;
```

**Did the Reapit recruiter click?** Filter to non-bot user-agents +
requests for `/` (the SPA landing):

```sql
SELECT
    from_iso8601_timestamp(time) AS request_time,
    client_ip,
    user_agent
FROM alb_logs
WHERE request_url LIKE '%//'
  AND user_agent NOT LIKE '%bot%'
  AND user_agent NOT LIKE '%spider%'
  AND from_iso8601_timestamp(time) > current_timestamp - interval '7' day
ORDER BY request_time DESC
LIMIT 50;
```

Take the `client_ip` value and run it through https://ipinfo.io or
similar — recruiters in Sydney/Brisbane will show as AU-based, often
with the ISP listed (e.g. "Telstra Internet", "Optus" for residential).

### Cost

Pennies/month for typical demo traffic:
- S3 storage: ~$0.025/GB; logs compress to <100 KB/day for low traffic
- Athena: $5 per TB scanned; each interactive query scans <1 MB

## Teardown

```bash
terraform destroy   # ~5 min; zero ongoing cost after
```

Note: `force_destroy = true` on the log + artefact buckets means
`terraform destroy` succeeds even with content still in them. Drop
that flag for production.

## Cost when running

| Resource             | Monthly |
|----------------------|---------|
| `db.t4g.micro` RDS   | ~$15    |
| 20 GB gp3 storage    | ~$2     |
| NAT Gateway          | ~$32    |
| ALB                  | ~$16    |
| Fargate (2 tasks)    | ~$10    |
| ECR storage          | ~$0.50  |
| Secrets Manager x1   | ~$0.40  |
| CloudWatch logs      | ~$1     |
| **Total**            | **~$77**|

Destroy when not demoing.
