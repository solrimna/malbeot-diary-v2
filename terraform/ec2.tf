# EC2 인스턴스 정의
# ami: 서버 OS 이미지 (main.tf의 data source에서 자동 조회한 Ubuntu 22.04)
# instance_type: 서버 사양 (t3.micro = 2vCPU, 1GB RAM)
# key_name: SSH 접속용 키페어 이름 (AWS 콘솔에서 발급한 것)
# vpc_security_group_ids: 위에서 만든 방화벽 규칙 연결

resource "aws_instance" "malbeot" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.malbeot.id]

  # 루트 볼륨 (기본 8GB → 20GB로 확장)
  # docker 이미지, 로그 등 용량 여유 확보
  root_block_device {
    volume_size = 20
    volume_type = "gp3"  # gp3 = gp2보다 저렴하고 빠름
  }

  # user_data: 인스턴스 최초 생성 시 자동 실행되는 스크립트
  # Docker + Docker Compose 설치 자동화
  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg

    # Docker 공식 GPG 키 추가
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Docker 저장소 추가
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list

    # Docker 설치
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # ubuntu 유저가 sudo 없이 docker 사용 가능하도록
    usermod -aG docker ubuntu
  EOF

  tags = {
    Name = var.project_name
  }
}

# 기존 Elastic IP를 새 인스턴스에 연결
# data source로 기존 EIP를 찾아서 새 인스턴스에 붙임
# → IP가 바뀌지 않아 duckdns, GitHub Secrets 수정 불필요
data "aws_eip" "existing" {
  public_ip = var.existing_eip
}

resource "aws_eip_association" "malbeot" {
  instance_id   = aws_instance.malbeot.id
  allocation_id = data.aws_eip.existing.id
}
