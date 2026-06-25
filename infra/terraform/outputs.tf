output "vpc_id" {
  description = "Provisioned VPC ID."
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "Provisioned public subnet ID."
  value       = aws_subnet.public.id
}

output "backend_security_group_id" {
  description = "Security group used by the backend host."
  value       = aws_security_group.backend.id
}

output "backend_instance_id" {
  description = "EC2 instance ID for backend host."
  value       = aws_instance.backend_host.id
}

output "backend_public_ip" {
  description = "Public IP of backend host."
  value       = aws_instance.backend_host.public_ip
}
