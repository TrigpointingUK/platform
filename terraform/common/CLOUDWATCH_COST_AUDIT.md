# CloudWatch Logs cost-audit access

Use the IAM role named `trigpointing-cloudwatch-cost-audit` for CloudWatch Logs
cost investigations. Terraform derives the `trigpointing` prefix from
`project_name`; use the `cloudwatch_cost_audit_role_arn` Terraform output rather
than constructing the ARN by hand.

The role is read-only. It can read Cost Explorer data, CloudWatch Logs group
metadata and ingestion metrics, and configuration metadata for common log
producers. It cannot read log events, change logging settings, or access
application data.

## Developer prerequisite

The role trusts this AWS account, but a role trust policy alone is insufficient.
Each developer's existing IAM/Identity Center permission set must also grant
`sts:AssumeRole` for the role ARN. Add the following statement to the relevant
developer permission set if it is not already covered by an existing role
assumption policy:

```json
{
  "Effect": "Allow",
  "Action": "sts:AssumeRole",
  "Resource": "arn:aws:iam::<AWS_ACCOUNT_ID>:role/trigpointing-cloudwatch-cost-audit"
}
```

## `~/.aws/config` profile

Keep developers' normal authenticated profile unchanged and add this entry to
`~/.aws/config`. Replace `trigpointing-admin` with the developer's existing
AWS SSO/IAM profile and replace the account ID with the value in the Terraform
role ARN output.

```ini
[profile trigpointing-cloudwatch-cost-audit]
role_arn = arn:aws:iam::<AWS_ACCOUNT_ID>:role/trigpointing-cloudwatch-cost-audit
source_profile = trigpointing-admin
role_session_name = codex-cloudwatch-cost-audit
duration_seconds = 3600
region = eu-west-1
output = json
```

Authenticate the source profile first (for SSO, `aws sso login --profile
trigpointing-admin`), then confirm access without exposing credentials:

```sh
aws sts get-caller-identity --profile trigpointing-cloudwatch-cost-audit
```

Agents can use the profile by setting `AWS_PROFILE=trigpointing-cloudwatch-cost-audit`.
Do not put access keys or session tokens in this repository or in chat.
