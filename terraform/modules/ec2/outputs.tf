# ============================================================================
# EC2 MODULE OUTPUTS
# ============================================================================

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.main.id
}

output "instance_arn" {
  description = "ARN of the EC2 instance"
  value       = aws_instance.main.arn
}

output "instance_state" {
  description = "State of the EC2 instance"
  value       = aws_instance.main.instance_state
}

output "public_ip" {
  description = "Public IP address of the instance"
  value       = aws_instance.main.public_ip
}

output "private_ip" {
  description = "Private IP address of the instance"
  value       = aws_instance.main.private_ip
}

output "public_dns" {
  description = "Public DNS name of the instance"
  value       = aws_instance.main.public_dns
}

output "private_dns" {
  description = "Private DNS name of the instance"
  value       = aws_instance.main.private_dns
}

output "availability_zone" {
  description = "Availability zone of the instance"
  value       = aws_instance.main.availability_zone
}

output "key_name" {
  description = "Key name of the instance"
  value       = aws_instance.main.key_name
}

output "security_groups" {
  description = "Security groups attached to the instance"
  value       = aws_instance.main.vpc_security_group_ids
}

output "elastic_ip" {
  description = "Elastic IP address (if created)"
  value       = var.associate_elastic_ip ? aws_eip.main[0].public_ip : null
}