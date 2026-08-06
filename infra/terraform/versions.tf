terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.90" # nécessaire pour aws_dsql_cluster
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2"
    }
    tls = {
      source  = "hashicorp/tls"
      version = ">= 4.0"
    }
  }

  # Backend d'état à adapter (S3 + verrouillage natif Terraform >= 1.10,
  # ou DynamoDB si vous restez sur un backend S3 classique).
  # backend "s3" {
  #   bucket = "optiprocure-terraform-state"
  #   key    = "optiprocure/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}
