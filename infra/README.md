# Sentinel — Infrastructure (Terraform)

Real IaC for the AWS deploy target, written so `terraform plan` validates for free
and `apply` can run against **AWS Free Tier** or **LocalStack** ($0).

## What it provisions
| Resource | Purpose |
|---|---|
| ECR ×3 | container images for the C#, TS, and Python services (pushed by CI) |
| RDS Postgres 16 (`db.t4g.micro`) | catalog, contracts, audit, eval, pgvector reg_chunks |
| S3 ×2 | regulation corpus (versioned) + run artifacts (eval reports, audit exports) |
| ECS Fargate cluster + 3 services | catalog / mcp / agent, with Container Insights |
| CloudWatch log groups | the monitoring backbone (per-service logs + Insights) |
| IAM roles | task execution (ECR pull, logs) + task role (S3 read corpus / write artifacts) |
| Security group | service ports + Postgres within the default VPC |

## Use
```bash
terraform init
terraform plan  -var-file=example.tfvars      # always free
terraform apply -var-file=example.tfvars       # AWS Free Tier
```

### $0 LocalStack path
```bash
pip install localstack terraform-local
localstack start -d
tflocal apply -var-file=example.tfvars -var use_localstack=true
```

## Scale notes (interview whiteboard)
- **10,000 facilities** → multi-tenant Postgres (row-level tenant isolation), ECS
  service autoscaling on CPU/SQS depth, regulation-corpus **versioning in S3** so a
  reg update is a reviewable, eval-gated deploy.
- **Eval-gated deploys** → CI runs the eval harness; a drop in compliance recall or
  grounding rate **blocks the rollout** (see `.github/workflows/ci.yml`).
- Frontier model spend is bounded by the per-request cost ceiling + Haiku/Opus routing.
