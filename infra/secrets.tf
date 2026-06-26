# --- secrets management (AWS Secrets Manager) ---
# The JWT signing secret and frontier-model API keys are stored in Secrets Manager
# and injected into ECS tasks as `secrets` (never baked into images or task env in
# plaintext). REQUIRE_STRONG_SECRETS=true makes the agent refuse to start with the
# default secret, so a misconfigured deploy fails fast instead of running insecure.

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "jwt" {
  name                    = "${local.name}/jwt-secret"
  recovery_window_in_days = 0
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = random_password.jwt.result
}

# Frontier-model keys — created empty; populate out-of-band (CLI/console), not in code.
resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "${local.name}/anthropic-api-key"
  recovery_window_in_days = 0
  tags                    = var.tags
}

resource "aws_secretsmanager_secret" "openai" {
  name                    = "${local.name}/openai-api-key"
  recovery_window_in_days = 0
  tags                    = var.tags
}

# allow the ECS task execution role to read these secrets at container start
data "aws_iam_policy_document" "secrets_read" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.jwt.arn,
      aws_secretsmanager_secret.anthropic.arn,
      aws_secretsmanager_secret.openai.arn,
    ]
  }
}

resource "aws_iam_role_policy" "exec_secrets" {
  name   = "${local.name}-exec-secrets"
  role   = aws_iam_role.exec.id
  policy = data.aws_iam_policy_document.secrets_read.json
}
