terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Default AWS provider. For $0 local runs, point at LocalStack by setting
# `use_localstack = true` (see localstack.tf) — `terraform plan` is always free.
provider "aws" {
  region                      = var.region
  s3_use_path_style           = var.use_localstack
  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack

  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      ecs            = "http://localhost:4566"
      ecr            = "http://localhost:4566"
      rds            = "http://localhost:4566"
      s3             = "http://localhost:4566"
      iam            = "http://localhost:4566"
      logs           = "http://localhost:4566"
      ec2            = "http://localhost:4566"
      cloudwatch     = "http://localhost:4566"
      secretsmanager = "http://localhost:4566"
    }
  }
}
