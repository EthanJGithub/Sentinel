variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "sentinel"
}

variable "use_localstack" {
  description = "Target LocalStack ($0) instead of real AWS."
  type        = bool
  default     = false
}

variable "db_username" {
  type    = string
  default = "sentinel"
}

variable "db_password" {
  type      = string
  sensitive = true
  default   = "sentinel-change-me"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro" # free-tier eligible
}

# the three containerized services (C#, TS, Python) -> ECR repos + ECS services
variable "services" {
  type = map(object({
    container_port = number
    cpu            = number
    memory         = number
  }))
  default = {
    catalog = { container_port = 8080, cpu = 256, memory = 512 }
    mcp     = { container_port = 7100, cpu = 256, memory = 512 }
    agent   = { container_port = 8000, cpu = 512, memory = 1024 }
  }
}

variable "tags" {
  type = map(string)
  default = {
    Project = "sentinel"
    Owner   = "ethan-jones"
    Purpose = "direct-supply-interview-demo"
  }
}
