
output "event_rule_arn" {
  description = "ARN of the created EventBridge rule"
  value       = aws_cloudwatch_event_rule.lambda_schedule.arn
}

output "event_rule_id" {
  description = "ID of the created EventBridge rule"
  value       = aws_cloudwatch_event_rule.lambda_schedule.id
}