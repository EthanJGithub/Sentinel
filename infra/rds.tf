# --- RDS Postgres (catalog, contracts, audit, eval, pgvector reg_chunks) ---
# Free-tier eligible (db.t4g.micro, 20GB). pgvector is available on RDS PG 15+.
resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db"
  subnet_ids = data.aws_subnets.default.ids
  tags       = var.tags
}

resource "aws_db_instance" "postgres" {
  identifier             = "${local.name}-pg"
  engine                 = "postgres"
  engine_version         = "16.4"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_type           = "gp3"
  db_name                = "sentinel"
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.svc.id]
  skip_final_snapshot    = true
  publicly_accessible    = false
  apply_immediately      = true
  tags                   = var.tags
}
