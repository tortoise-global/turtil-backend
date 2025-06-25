# AMI Module - Use base Ubuntu AMI directly for now
# TODO: Add custom AMI creation in the future

# Get base Ubuntu AMI for ARM64
data "aws_ami" "ubuntu_base" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }
  
  filter {
    name   = "architecture"
    values = ["arm64"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}