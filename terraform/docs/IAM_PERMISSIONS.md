# IAM Permissions Required for Terraform Infrastructure

## Overview
This document lists the specific IAM permissions required to deploy and manage the Turtil Backend multi-environment infrastructure using Terraform.

## 🔐 Core AWS Services Permissions

### 1. **S3 Permissions** (for buckets and Terraform state)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:GetBucketAcl",
                "s3:GetBucketCORS",
                "s3:GetBucketEncryption",
                "s3:GetBucketLifecycleConfiguration",
                "s3:GetBucketLocation",
                "s3:GetBucketLogging",
                "s3:GetBucketNotification",
                "s3:GetBucketPolicy",
                "s3:GetBucketPublicAccessBlock",
                "s3:GetBucketRequestPayment",
                "s3:GetBucketTagging",
                "s3:GetBucketVersioning",
                "s3:GetBucketWebsite",
                "s3:GetEncryptionConfiguration",
                "s3:GetIntelligentTieringConfiguration",
                "s3:GetLifecycleConfiguration",
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:GetObjectVersion",
                "s3:ListBucket",
                "s3:ListBucketVersions",
                "s3:PutBucketAcl",
                "s3:PutBucketCORS",
                "s3:PutBucketEncryption",
                "s3:PutBucketLifecycleConfiguration",
                "s3:PutBucketLogging",
                "s3:PutBucketNotification",
                "s3:PutBucketPolicy",
                "s3:PutBucketPublicAccessBlock",
                "s3:PutBucketRequestPayment",
                "s3:PutBucketTagging",
                "s3:PutBucketVersioning",
                "s3:PutBucketWebsite",
                "s3:PutEncryptionConfiguration",
                "s3:PutIntelligentTieringConfiguration",
                "s3:PutLifecycleConfiguration",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:DeleteObject",
                "s3:DeleteObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::turtil-backend-*",
                "arn:aws:s3:::turtil-backend-*/*"
            ]
        }
    ]
}
```

### 2. **RDS Permissions** (for PostgreSQL and Aurora)
```json
{
    "Effect": "Allow",
    "Action": [
        "rds:CreateDBInstance",
        "rds:CreateDBSubnetGroup",
        "rds:CreateDBParameterGroup",
        "rds:CreateDBCluster",
        "rds:CreateDBClusterParameterGroup",
        "rds:DeleteDBInstance",
        "rds:DeleteDBSubnetGroup",
        "rds:DeleteDBParameterGroup",
        "rds:DeleteDBCluster",
        "rds:DeleteDBClusterParameterGroup",
        "rds:DescribeDBInstances",
        "rds:DescribeDBSubnetGroups",
        "rds:DescribeDBParameterGroups",
        "rds:DescribeDBClusters",
        "rds:DescribeDBClusterParameterGroups",
        "rds:DescribeDBEngineVersions",
        "rds:DescribeOrderableDBInstanceOptions",
        "rds:ModifyDBInstance",
        "rds:ModifyDBSubnetGroup",
        "rds:ModifyDBParameterGroup",
        "rds:ModifyDBCluster",
        "rds:ModifyDBClusterParameterGroup",
        "rds:AddTagsToResource",
        "rds:ListTagsForResource",
        "rds:RemoveTagsFromResource",
        "rds:CreateDBSnapshot",
        "rds:DeleteDBSnapshot",
        "rds:DescribeDBSnapshots",
        "rds:RestoreDBInstanceFromDBSnapshot"
    ],
    "Resource": "*"
}
```

### 3. **ECR Permissions** (for container registry)
```json
{
    "Effect": "Allow",
    "Action": [
        "ecr:CreateRepository",
        "ecr:DeleteRepository",
        "ecr:DescribeRepositories",
        "ecr:GetRepositoryPolicy",
        "ecr:SetRepositoryPolicy",
        "ecr:DeleteRepositoryPolicy",
        "ecr:GetLifecyclePolicy",
        "ecr:PutLifecyclePolicy",
        "ecr:DeleteLifecyclePolicy",
        "ecr:GetRegistryScanningConfiguration",
        "ecr:PutRegistryScanningConfiguration",
        "ecr:TagResource",
        "ecr:UntagResource",
        "ecr:ListTagsForResource"
    ],
    "Resource": "*"
}
```

### 4. **VPC and Networking Permissions**
```json
{
    "Effect": "Allow",
    "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeInternetGateways",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroups",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:CreateTags",
        "ec2:DescribeTags"
    ],
    "Resource": "*"
}
```

### 5. **Load Balancer Permissions** (if using ALB module)
```json
{
    "Effect": "Allow",
    "Action": [
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeLoadBalancerAttributes",
        "elasticloadbalancing:ModifyLoadBalancerAttributes",
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:DeleteTargetGroup",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetGroupAttributes",
        "elasticloadbalancing:ModifyTargetGroupAttributes",
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:DeleteListener",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:CreateRule",
        "elasticloadbalancing:DeleteRule",
        "elasticloadbalancing:DescribeRules",
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:RemoveTags",
        "elasticloadbalancing:DescribeTags"
    ],
    "Resource": "*"
}
```

### 6. **CloudFront Permissions** (for production CDN)
```json
{
    "Effect": "Allow",
    "Action": [
        "cloudfront:CreateDistribution",
        "cloudfront:DeleteDistribution",
        "cloudfront:GetDistribution",
        "cloudfront:GetDistributionConfig",
        "cloudfront:ListDistributions",
        "cloudfront:UpdateDistribution",
        "cloudfront:TagResource",
        "cloudfront:UntagResource",
        "cloudfront:ListTagsForResource"
    ],
    "Resource": "*"
}
```

## 🎯 **Complete IAM Policy (Recommended)**

### Option 1: Single Comprehensive Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*",
                "rds:*",
                "ecr:*",
                "ec2:Describe*",
                "ec2:CreateSecurityGroup",
                "ec2:DeleteSecurityGroup",
                "ec2:AuthorizeSecurityGroup*",
                "ec2:RevokeSecurityGroup*",
                "ec2:CreateTags",
                "elasticloadbalancing:*",
                "cloudfront:*"
            ],
            "Resource": "*"
        }
    ]
}
```

### Option 2: AWS Managed Policies (Easier but broader permissions)
Attach these AWS managed policies to your IAM user/role:

```bash
# Core infrastructure management
- PowerUserAccess

# Or more specific managed policies:
- AmazonS3FullAccess
- AmazonRDSFullAccess
- AmazonEC2ContainerRegistryFullAccess
- ElasticLoadBalancingFullAccess
- CloudFrontFullAccess
- AmazonVPCReadOnlyAccess
```

## 🔧 **Setup Instructions**

### Method 1: Create IAM User for Terraform
1. **Create IAM User:**
   ```bash
   aws iam create-user --user-name terraform-turtil-backend
   ```

2. **Attach Policy:**
   ```bash
   # Using managed policy (easier)
   aws iam attach-user-policy --user-name terraform-turtil-backend --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
   
   # Or create and attach custom policy
   aws iam put-user-policy --user-name terraform-turtil-backend --policy-name TurtilBackendTerraform --policy-document file://terraform-policy.json
   ```

3. **Create Access Keys:**
   ```bash
   aws iam create-access-key --user-name terraform-turtil-backend
   ```

### Method 2: Use IAM Role (for CI/CD)
If deploying from GitHub Actions or other CI/CD:

1. **Create IAM Role with Trust Policy:**
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Principal": {
                   "Federated": "arn:aws:iam::ACCOUNT-ID:oidc-provider/token.actions.githubusercontent.com"
               },
               "Action": "sts:AssumeRoleWithWebIdentity",
               "Condition": {
                   "StringEquals": {
                       "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                       "token.actions.githubusercontent.com:sub": "repo:your-username/turtil-backend:ref:refs/heads/main"
                   }
               }
           }
       ]
   }
   ```

## 🚨 **Security Best Practices**

### 1. **Principle of Least Privilege**
- Start with the minimal permissions and add more as needed
- Use resource-specific ARNs where possible
- Remove unused permissions regularly

### 2. **Environment Separation**
- Use different IAM roles/users for different environments
- Tag resources appropriately for cost tracking and access control

### 3. **Credentials Management**
- Never commit AWS credentials to version control
- Use AWS Secrets Manager or Parameter Store for sensitive values
- Rotate access keys regularly

### 4. **Monitoring and Auditing**
- Enable CloudTrail for API logging
- Set up IAM Access Analyzer
- Monitor unusual access patterns

## 📋 **Environment-Specific Considerations**

### Development Environment
- Can use broader permissions for faster development
- Consider using IAM user with programmatic access

### Testing Environment  
- Similar to development but with some restrictions
- Good place to test IAM permission boundaries

### Production Environment
- Use most restrictive permissions possible
- Prefer IAM roles over users
- Enable MFA for critical operations
- Use AWS Organizations SCPs for additional guardrails

## 🔍 **Troubleshooting Common Permission Issues**

### 1. **S3 Backend Access Denied**
```bash
# Ensure these permissions for Terraform state bucket:
s3:GetObject, s3:PutObject, s3:DeleteObject
s3:ListBucket
```

### 2. **RDS Creation Fails**
```bash
# Common missing permissions:
rds:DescribeDBSubnetGroups
ec2:DescribeVpcs
ec2:DescribeSubnets
```

### 3. **ECR Repository Issues**
```bash
# Ensure ECR permissions include:
ecr:CreateRepository
ecr:DescribeRepositories
ecr:PutLifecyclePolicy
```

## 📚 **Useful Commands**

### Check Current Permissions
```bash
# List attached policies
aws iam list-attached-user-policies --user-name terraform-turtil-backend

# Test specific permissions
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::ACCOUNT:user/terraform-turtil-backend --action-names s3:CreateBucket
```

### Validate Terraform with Current Permissions
```bash
# Dry run to check permissions
terraform plan -var-file="environments/development.tfvars"
```

---

**Note**: Replace `ACCOUNT-ID` and `your-username` with your actual AWS account ID and GitHub username respectively.