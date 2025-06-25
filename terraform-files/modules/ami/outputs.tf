output "ami_id" {
  description = "AMI ID (existing or newly created)"
  value       = data.aws_ami.existing_ami.id != null ? data.aws_ami.existing_ami.id : aws_ami_from_instance.custom_ami[0].id
}

output "ami_name" {
  description = "AMI name"
  value       = data.aws_ami.existing_ami.id != null ? data.aws_ami.existing_ami.name : aws_ami_from_instance.custom_ami[0].name
}

output "ami_creation_date" {
  description = "AMI creation date"
  value       = data.aws_ami.existing_ami.id != null ? data.aws_ami.existing_ami.creation_date : aws_ami_from_instance.custom_ami[0].creation_date
}

output "ami_architecture" {
  description = "AMI architecture"
  value       = "arm64"
}

output "ami_status" {
  description = "Whether AMI was created new or existed"
  value       = data.aws_ami.existing_ami.id != null ? "existing" : "newly_created"
}