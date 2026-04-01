# Security Group = AWS 방화벽
# EC2 인스턴스에 붙이는 규칙 집합
# ingress: 들어오는 트래픽 허용 규칙
# egress: 나가는 트래픽 허용 규칙

resource "aws_security_group" "malbeot" {
  name        = "${var.project_name}-sg"
  description = "말벗 서비스 보안 그룹"

  # SSH 접속 (22번 포트)
  # 터미널에서 EC2에 직접 접속할 때 사용
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # 모든 IP 허용 (고정 IP 있으면 본인 IP만 허용 권장)
  }

  # HTTP (80번 포트)
  # Nginx가 받아서 HTTPS로 리다이렉트
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS (443번 포트)
  # Let's Encrypt SSL 인증서로 암호화된 실제 트래픽
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 나가는 트래픽 전체 허용
  # Docker 이미지 pull, OpenAI API 호출 등에 필요
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"  # -1 = 모든 프로토콜
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}
