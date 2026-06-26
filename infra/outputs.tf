output "ecr_repos" {
  description = "ECR repository URLs (push targets for CI)."
  value       = { for k, r in aws_ecr_repository.svc : k => r.repository_url }
}

output "rds_endpoint" {
  description = "Postgres endpoint for the services."
  value       = aws_db_instance.postgres.address
}

output "reg_corpus_bucket" {
  value = aws_s3_bucket.regs.bucket
}

output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "log_groups" {
  value = { for k, g in aws_cloudwatch_log_group.svc : k => g.name }
}
