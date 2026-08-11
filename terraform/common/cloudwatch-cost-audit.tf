# Read-only role for investigating CloudWatch Logs ingestion charges.
#
# The role deliberately cannot read log events or change account resources.  It
# is intended for human and agent-assisted cost investigations only.
resource "aws_iam_role" "cloudwatch_cost_audit" {
  name                 = "${var.project_name}-cloudwatch-cost-audit"
  max_session_duration = 3600

  # The account root principal does not grant every principal in this account
  # permission to assume the role.  Each developer's existing IAM/SSO
  # permission set must also allow sts:AssumeRole for this role ARN.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowAccountPrincipalsWithAssumeRolePermission"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-cloudwatch-cost-audit"
    Purpose = "Read-only CloudWatch Logs cost investigation"
  }
}

resource "aws_iam_role_policy" "cloudwatch_cost_audit" {
  name = "${var.project_name}-cloudwatch-cost-audit"
  role = aws_iam_role.cloudwatch_cost_audit.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadCostExplorer"
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostAndUsageWithResources",
          "ce:GetDimensionValues",
          "ce:GetTags"
        ]
        Resource = "*"
      },
      {
        Sid    = "ReadCloudWatchLogVolume"
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "logs:DescribeLogGroups",
          "logs:DescribeSubscriptionFilters",
          "logs:ListTagsForResource"
        ]
        Resource = "*"
      },
      {
        Sid    = "IdentifyCommonLogProducers"
        Effect = "Allow"
        Action = [
          "apigateway:GET",
          "cloudtrail:DescribeTrails",
          "cloudtrail:GetTrailStatus",
          "ec2:DescribeFlowLogs",
          "ecs:DescribeClusters",
          "ecs:DescribeServices",
          "ecs:ListClusters",
          "ecs:ListServices",
          "eks:DescribeCluster",
          "eks:ListClusters",
          "elasticloadbalancing:DescribeLoadBalancers",
          "lambda:GetFunctionConfiguration",
          "lambda:ListFunctions",
          "rds:DescribeDBInstances",
          "route53resolver:ListResolverQueryLogConfigAssociations",
          "route53resolver:ListResolverQueryLogConfigs",
          "wafv2:GetLoggingConfiguration"
        ]
        Resource = "*"
      }
    ]
  })
}
