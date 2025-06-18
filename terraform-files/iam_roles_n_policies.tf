


# IAM Role for EC2 to access ECR
resource "aws_iam_role" "ec2_ecr_access" {
  name = "${terraform.workspace}-ec2-cms-ecr-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = lookup(var.ec2_env_tags, terraform.workspace)
  }
}

# Custom policy for ECR access
resource "aws_iam_role_policy" "ecr_access" {
  name = "${terraform.workspace}-cms-ecr-access-policy"
  role = aws_iam_role.ec2_ecr_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories",
          "ecr:ListImages"
        ]
        Resource = "*"
      }
    ]
  })
}

# Custom policy for SSM and KMS access
resource "aws_iam_role_policy" "ssm_kms_access" {
  name = "${terraform.workspace}-cms-ssm-kms-access-policy"
  role = aws_iam_role.ec2_ecr_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ssm:*"
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

# Attach AWS managed SSM policy for Systems Manager access
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.ec2_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Create an instance profile for the role
resource "aws_iam_instance_profile" "ec2_ecr_access" {
  name = "${terraform.workspace}-ec2-cms-ecr-access-profile"
  role = aws_iam_role.ec2_ecr_access.name
}