# Copy to terraform.tfvars and adjust. For a $0 dry run:
#   terraform init && terraform plan -var-file=example.tfvars
# To apply against LocalStack (also $0):
#   use_localstack = true   (then `tflocal apply` or set the endpoints above)

region            = "us-east-1"
project           = "sentinel"
use_localstack    = false
db_username       = "sentinel"
db_password       = "change-me-please"
db_instance_class = "db.t4g.micro"
