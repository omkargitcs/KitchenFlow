terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Latest Amazon Linux 2023 image
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# Firewall: web traffic in, everything out
resource "aws_security_group" "api" {
  name        = "${var.name}-api"
  description = "Allow HTTP to the KitchenFlow API"

  ingress {
    description = "API"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Project = var.name }
}

# One small server that pulls the code from GitHub and runs it under systemd
resource "aws_instance" "api" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.api.id]

  user_data = templatefile("${path.module}/user_data.sh", {
    repo_url = var.repo_url
    api_key  = var.api_key
  })
  user_data_replace_on_change = true

  tags = { Name = var.name, Project = var.name }
}
