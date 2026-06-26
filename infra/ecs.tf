# --- ECS Fargate cluster + one service per container (catalog, mcp, agent) ---
resource "aws_ecs_cluster" "main" {
  name = "${local.name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled" # CloudWatch Container Insights = the monitoring backbone
  }
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "svc" {
  for_each          = var.services
  name              = "/ecs/${local.name}/${each.key}"
  retention_in_days = 14
  tags              = var.tags
}

# --- IAM: task execution role (pull from ECR, write logs) ---
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "exec" {
  name               = "${local.name}-ecs-exec"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "exec" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# task role: read regulation corpus + write artifacts to S3
resource "aws_iam_role" "task" {
  name               = "${local.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

data "aws_iam_policy_document" "task" {
  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.regs.arn, "${aws_s3_bucket.regs.arn}/*"]
  }
  statement {
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.artifacts.arn}/*"]
  }
}

resource "aws_iam_role_policy" "task" {
  name   = "${local.name}-task-s3"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task.json
}

# --- task definitions + services (parameterized over the 3 services) ---
resource "aws_ecs_task_definition" "svc" {
  for_each                 = var.services
  family                   = "${local.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.exec.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = each.key
    image     = "${aws_ecr_repository.svc[each.key].repository_url}:latest"
    essential = true
    portMappings = [{
      containerPort = each.value.container_port
      protocol      = "tcp"
    }]
    environment = [
      { name = "DATA_DIR", value = "/data" },
      { name = "CATALOG_URL", value = "http://catalog.${local.name}.local:8080" },
      { name = "MCP_URL", value = "http://mcp.${local.name}.local:7100" },
    ]
    secrets = []
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.svc[each.key].name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = each.key
      }
    }
  }])
  tags = var.tags
}

resource "aws_ecs_service" "svc" {
  for_each        = var.services
  name            = each.key
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.svc[each.key].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.svc.id]
    assign_public_ip = true
  }
  tags = var.tags
}
