# Data source for AMI (flexible for Ubuntu, Amazon Linux, etc.)
data "aws_ami" "selected" {
  most_recent = true
  owners      = [var.ami_owner]

  filter {
    name   = "name"
    values = [var.ami_name_filter]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Data source to get the VPC
data "aws_vpc" "selected" {
  id      = var.vpc_id != "" ? var.vpc_id : null
  default = var.vpc_id == "" ? true : null
}

# Data source to get the subnet
data "aws_subnet" "selected" {
  vpc_id            = data.aws_vpc.selected.id
  availability_zone = var.availability_zone
}

# Create a security group for the EC2 instance
resource "aws_security_group" "ec2_sg" {
  name        = "${var.instance_name}-sg"
  description = "Security group for EC2 instance ${var.instance_name}"
  vpc_id      = data.aws_vpc.selected.id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      description = ingress.value.description
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = [ingress.value.cidr_block]
    }
  }

  # Conditionally add ingress rule for ALB traffic
  dynamic "ingress" {
    for_each = var.alb_security_group_id != null ? [1] : []
    content {
      description     = "HTTP from ALB"
      from_port       = 80
      to_port         = 80
      protocol        = "tcp"
      security_groups = [var.alb_security_group_id]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.instance_name}-sg"
  })
}

# Create an EC2 instance
resource "aws_instance" "this" {
  ami                    = data.aws_ami.selected.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnet.selected.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  key_name               = var.key_name
  user_data              = var.user_data

  root_block_device {
    volume_size = var.root_block_device_size
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(var.tags, {
    Name = var.instance_name
  })
}