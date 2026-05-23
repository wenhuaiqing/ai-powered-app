# infra/

Terraform for the ai-powered-app AWS footprint. **Phase 2 step 0** lands
the data layer (network + RDS MySQL + Secrets Manager). Compute (ECS
Fargate + ALB), the Bedrock provider toggle, ECR for the backend image,
and the GitHub Actions OIDC deploy follow in subsequent steps.

## What's here

| File | What it provisions |
|---|---|
| `versions.tf`   | Terraform + AWS provider pins |
| `variables.tf`  | region, env, instance sizing, allowed CIDRs |
| `network.tf`    | VPC (2 AZs), public + private subnets, IGW, NAT Gateway, route tables |
| `rds.tf`        | `aws_db_subnet_group` + security group + `db.t4g.micro` MySQL 8 in private subnets |
| `secrets.tf`    | `random_password` -> `aws_secretsmanager_secret` (the app reads this at runtime via the task role) |
| `iam.tf`        | ECS task execution role + task role (reads the secret; later: Bedrock invoke) |
| `seed_task.tf`  | One-shot ECS task definition that runs `scripts/seed_all.py` against the new DB. Cluster is created in this step so `aws ecs run-task` works the moment a backend image lands in ECR (Phase 2 step 2). |
| `outputs.tf`    | RDS endpoint, secret ARN, subnet IDs, security group IDs |

## What's deliberately omitted

- **ALB + ECS services** — Phase 2 step 3 (separate PR).
- **ECR repository** — Phase 2 step 2, lands with the Dockerfiles.
- **GitHub OIDC + deploy workflow** — Phase 2 step 4.
- **Autoscaling, multi-AZ RDS, WAF, custom domain, ACM** — overkill for a
  portfolio demo. Document the upgrade path in a "Production posture"
  section of the root README rather than building it.

## How to apply (first time)

```bash
cd infra
terraform init
terraform plan       # review — should create ~20 resources
terraform apply
```

RDS provisioning takes ~8 minutes. The rest comes up in under a minute.
After apply, `terraform output -raw rds_endpoint` gives you the host.

## Seeding the database

The seed task definition runs `scripts/seed_all.py` inside the VPC. It
needs the backend image (built in Phase 2 step 2) in ECR. Once that
image exists:

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

The task pulls the secret via the task role, runs migrate -> build -> ETL,
exits. Logs land in `/aws/ecs/ai-powered-app/seed`.

## Teardown

```bash
terraform destroy
```

Takes ~5 minutes (RDS deletion is slow). Zero ongoing cost after.

## Cost when running

| Resource             | Monthly |
|----------------------|---------|
| `db.t4g.micro` RDS   | ~$15    |
| 20 GB gp3 storage    | ~$2     |
| NAT Gateway          | ~$32    |
| Secrets Manager (x1) | ~$0.40  |
| **Total**            | **~$50**|

Destroy when not demoing.
