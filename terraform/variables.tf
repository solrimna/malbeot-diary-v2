# 변수 선언 파일
# 여기선 변수의 이름, 타입, 설명만 정의
# 실제 값은 terraform.tfvars 에 작성 (git에 올리지 않음)

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"  # 서울 리전 기본값
}

variable "instance_type" {
  description = "EC2 인스턴스 유형"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "EC2 접속에 사용할 키페어 이름 (AWS 콘솔에서 생성한 것)"
  type        = string
}

variable "project_name" {
  description = "리소스 이름 태그에 사용할 프로젝트명"
  type        = string
  default     = "malbeot"
}

variable "existing_eip" {
  description = "기존 Elastic IP 주소 - 새 인스턴스에 재사용해 IP 변경 없이 유지"
  type        = string
}
