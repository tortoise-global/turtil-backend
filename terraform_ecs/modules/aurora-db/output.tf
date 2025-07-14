output "cluster_id" {
  description = "Aurora cluster ID"
  value       = aws_rds_cluster.this.id
}

output "writer_endpoint" {
  description = "Primary writer endpoint"
  value       = aws_rds_cluster.this.endpoint
}

output "security_group_id" {
  description = "Aurora security group ID"
  value       = aws_security_group.aurora.id
}
