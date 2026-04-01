# outputs.tf - terraform apply 완료 후 터미널에 출력되는 안내 메시지
#
# 실제로 뭔가를 실행하거나 연결해주는 게 아니라 "다음에 이렇게 하세요" 알려주는 가이드 역할
# apply 완료 시 아래처럼 출력됨:
#
#   Outputs:
#   instance_id = "i-0a1b2c3d4e5f"
#   public_ip   = "3.36.242.123"
#   ssh_command = "ssh -i ~/.ssh/malbeot.pem ubuntu@3.36.242.123"
#
# ssh_command 출력값을 복사해서 cmd에 붙여넣으면 EC2에 접속 가능
# 단, malbeot.pem 파일이 로컬 ~/.ssh/ 경로에 있어야 함 (AWS 콘솔에서 키페어 생성 시 받은 파일)

output "instance_id" {
  description = "EC2 인스턴스 ID"
  value       = aws_instance.malbeot.id
}

output "public_ip" {
  description = "Elastic IP (고정 공인 IP) - 기존 IP 재사용"
  value       = var.existing_eip
}

output "ssh_command" {
  description = "EC2 SSH 접속 명령어"
  value       = "ssh -i ~/.ssh/malbeot.pem ubuntu@${var.existing_eip}"
}
