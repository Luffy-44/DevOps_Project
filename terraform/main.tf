# ─── Lookup Latest Ubuntu 24.04 LTS AMI ────────────────────────────────────────
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ─── Security Group for EC2 Backend & Frontend ────────────────────────────────
resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-ec2-sg"
  description = "Security group for Zestora web application on EC2"
  vpc_id      = aws_vpc.main.id

  # Inbound HTTP from ALB and direct
  ingress {
    description = "Allow inbound HTTP from ALB and Direct"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH - Remote administrative access
  ingress {
    description = "Allow inbound SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_ip_cidr]
  }

  # Inbound Prometheus Monitoring (Port 9090)
  ingress {
    description = "Prometheus Metrics Server"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Inbound Grafana Dashboard (Port 3000 / 3002)
  ingress {
    description = "Grafana Visual Dashboards"
    from_port   = 3002
    to_port     = 3002
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress - Outbound traffic
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ec2-sg"
    Environment = var.environment
  }
}

# ─── EC2 Application Server ───────────────────────────────────────────────────
resource "aws_instance" "web" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public_1.id
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  key_name                    = var.ssh_key_name != "" ? var.ssh_key_name : null
  associate_public_ip_address = true

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name = "${var.project_name}-root-ebs"
    }
  }

  # Bootstraps Docker, Swap memory, and auto-lifecycle timer
  user_data = file("${path.module}/../ec2-user-data.sh")

  tags = {
    Name        = "${var.project_name}-server"
    Environment = var.environment
  }
}
