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

## Teardown

```bash
terraform destroy   # ~5 min; zero ongoing cost after
```

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
