# Terraform 자체 설정
# required_providers: 어떤 클라우드 SDK를 쓸지 선언 (여기선 AWS)
# required_version: Terraform CLI 최소 버전
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # AWS provider 5.x 버전 사용
    }
  }
  required_version = ">= 1.6"
}

# AWS provider 설정
# region은 variables.tf에 선언된 변수를 참조
provider "aws" {
  region = var.aws_region
}

# 최신 Ubuntu 22.04 LTS AMI를 자동으로 찾아오는 데이터 소스
# AMI ID는 리전마다 다르고 버전업되므로 하드코딩 대신 data source로 조회
# owners: Canonical(Ubuntu 공식 배포사) 계정 ID
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}
