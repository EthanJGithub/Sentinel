locals {
  name = var.project
}

# --- networking: use the account's default VPC + subnets (keeps the demo lean) ---
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# --- ECR: one repo per containerized service (pushed by GitHub Actions) ---
resource "aws_ecr_repository" "svc" {
  for_each             = var.services
  name                 = "${local.name}/${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = var.tags
}

# --- S3: regulation corpus + run artifacts (eval reports, audit exports) ---
resource "aws_s3_bucket" "regs" {
  bucket        = "${local.name}-reg-corpus-${var.region}"
  force_destroy = true
  tags          = var.tags
}

resource "aws_s3_bucket" "artifacts" {
  bucket        = "${local.name}-artifacts-${var.region}"
  force_destroy = true
  tags          = var.tags
}

resource "aws_s3_bucket_versioning" "regs" {
  bucket = aws_s3_bucket.regs.id
  versioning_configuration {
    status = "Enabled" # regulation-corpus versioning -> reproducible eval at deploy time
  }
}

# --- security group: allow service ports within the VPC ---
resource "aws_security_group" "svc" {
  name        = "${local.name}-svc"
  description = "Sentinel services"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "service ports"
    from_port   = 7000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }
  ingress {
    description = "postgres"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = var.tags
}
