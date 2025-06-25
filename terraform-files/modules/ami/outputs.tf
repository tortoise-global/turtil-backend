output "ami_id" {
  description = "AMI ID (base Ubuntu ARM64)"
  value       = data.aws_ami.ubuntu_base.id
}

output "ami_name" {
  description = "AMI name"
  value       = data.aws_ami.ubuntu_base.name
}

output "ami_creation_date" {
  description = "AMI creation date"
  value       = data.aws_ami.ubuntu_base.creation_date
}

output "ami_architecture" {
  description = "AMI architecture"
  value       = "arm64"
}

output "ami_status" {
  description = "AMI source"
  value       = "base_ubuntu"
}