# ============================================================================
# TERRAFORM VARIABLES - ENVIRONMENT VARIABLE DRIVEN CONFIGURATION
# ============================================================================
# 
# This file should NOT contain hardcoded sensitive values.
# All sensitive values should be provided via environment variables.
# 
# For local development, use: source loadenv.sh
# For CI/CD, use GitHub Secrets
# 
# Required Environment Variables:
# - TF_VAR_app_database_url
# - TF_VAR_app_secret_key
# - TF_VAR_app_aws_access_key_id
# - TF_VAR_app_aws_secret_access_key
# - TF_VAR_app_s3_bucket_name
# - TF_VAR_app_upstash_redis_url
# - TF_VAR_app_upstash_redis_token
# - TF_VAR_app_otp_secret
# - TF_VAR_app_jwt_secret_key
# - TF_VAR_app_environment (development/production)
# - TF_VAR_app_debug (true/false)
# 
# Optional Environment Variables (have defaults):
# - TF_VAR_app_algorithm (default: HS256)
# - TF_VAR_app_access_token_expire_minutes (default: 30)
# - TF_VAR_app_project_name (default: "Turtil Backend")
# - TF_VAR_app_version (default: "1.0.0")
# - TF_VAR_app_log_level (default: "INFO")
# - TF_VAR_app_rate_limit_calls (default: "100")
# - TF_VAR_app_rate_limit_period (default: "60")
# - TF_VAR_app_otp_expiry_minutes (default: "5")
# - TF_VAR_app_aws_default_region (default: "ap-south-1")
# - TF_VAR_app_redis_user_cache_ttl (default: "300")
# - TF_VAR_app_redis_blacklist_ttl (default: "86400")
# - TF_VAR_app_aws_ses_from_email (default: "support@turtil.co")
# - TF_VAR_app_aws_ses_region (default: "ap-south-1")
# - TF_VAR_app_aws_region (default: "ap-south-1")
# - TF_VAR_app_cors_origins (default: ["*", "http://localhost:3000", "http://localhost:8080"])
# - TF_VAR_app_allowed_hosts (default: ["*", "localhost", "127.0.0.1", "0.0.0.0"])
# - TF_VAR_app_jwt_algorithm (default: "HS256")
# - TF_VAR_app_jwt_expire_minutes (default: 30)
# 
# ============================================================================

# Non-sensitive values can be set here (optional - these have defaults)
# app_algorithm = "HS256"
# app_access_token_expire_minutes = "30"
# app_project_name = "Turtil Backend"
# app_version = "1.0.0"
# app_log_level = "INFO"
# app_rate_limit_calls = "100"
# app_rate_limit_period = "60"
# app_otp_expiry_minutes = "5"
# app_aws_default_region = "ap-south-1"
# app_redis_user_cache_ttl = "300"
# app_redis_blacklist_ttl = "86400"
# app_aws_ses_from_email = "support@turtil.co"
# app_aws_ses_region = "ap-south-1"