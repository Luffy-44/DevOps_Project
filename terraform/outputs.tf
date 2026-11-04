output "vpc_id" {
  description = "Custom VPC ID"
  value       = aws_vpc.main.id
}

output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.web.public_ip
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS Name (Main Ingress)"
  value       = "http://${aws_lb.app_alb.dns_name}"
}

output "cloudfront_url" {
  description = "Global CloudFront CDN Distribution URL"
  value       = "https://${aws_cloudfront_distribution.app_cdn.domain_name}"
}

output "ecr_frontend_repo" {
  description = "AWS ECR Repository for Frontend Docker image"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecr_backend_repo" {
  description = "AWS ECR Repository for Backend Docker image"
  value       = aws_ecr_repository.backend.repository_url
}

output "prometheus_url" {
  description = "Prometheus Metrics Explorer"
  value       = "http://${aws_instance.web.public_ip}:9090"
}

output "grafana_url" {
  description = "Grafana Observability Dashboard"
  value       = "http://${aws_instance.web.public_ip}:3002"
}

output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = var.ssh_key_name != "" ? "ssh -i ${var.ssh_key_name}.pem ubuntu@${aws_instance.web.public_ip}" : "ssh -i adm.pem ubuntu@${aws_instance.web.public_ip}"
}
