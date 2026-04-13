# Data Archive Email Troubleshooting

Queries and procedures for investigating archive delivery issues.

The `user_archive` table records every archive generation attempt with
status, size, timestamps, and error messages. SES message IDs are in
CloudWatch logs (not in the database).

## Common queries

### Did user X receive an archive?

```sql
-- By username
SELECT ua.id, ua.status, ua.frequency_at_send, ua.format_at_send,
       ua.log_count, ua.file_size_bytes, ua.error_message, ua.created_at
  FROM user_archive ua
  JOIN "user" u ON u.id = ua.user_id
 WHERE u.name = 'someuser'
 ORDER BY ua.created_at DESC
 LIMIT 20;

-- By user_id
SELECT * FROM user_archive
 WHERE user_id = 12345
 ORDER BY created_at DESC
 LIMIT 20;
```

### Were any duplicates sent?

Archives sent more than once to the same user on the same calendar day.

```sql
SELECT ua.user_id, u.name, DATE(ua.created_at) AS send_date,
       COUNT(*) AS times_sent
  FROM user_archive ua
  JOIN "user" u ON u.id = ua.user_id
 WHERE ua.status = 'S'
 GROUP BY ua.user_id, u.name, DATE(ua.created_at)
HAVING COUNT(*) > 1
 ORDER BY send_date DESC;
```

### What failed recently?

```sql
SELECT ua.id, ua.user_id, u.name, ua.error_message,
       ua.format_at_send, ua.created_at
  FROM user_archive ua
  JOIN "user" u ON u.id = ua.user_id
 WHERE ua.status = 'F'
   AND ua.created_at >= NOW() - INTERVAL '7 days'
 ORDER BY ua.created_at DESC;
```

### Daily send volume (last 30 days)

```sql
SELECT DATE(created_at) AS send_date,
       COUNT(*) FILTER (WHERE status = 'S') AS sent,
       COUNT(*) FILTER (WHERE status = 'F') AS failed,
       COUNT(*) AS total
  FROM user_archive
 WHERE created_at >= NOW() - INTERVAL '30 days'
 GROUP BY DATE(created_at)
 ORDER BY send_date DESC;
```

### Largest archives

Useful for monitoring SES attachment size limits (10 MB raw).

```sql
SELECT ua.user_id, u.name, ua.log_count, ua.file_size_bytes,
       ua.format_at_send, ua.created_at
  FROM user_archive ua
  JOIN "user" u ON u.id = ua.user_id
 WHERE ua.status = 'S'
 ORDER BY ua.file_size_bytes DESC
 LIMIT 20;
```

### Users with archive enabled but never received one

```sql
SELECT u.id, u.name, u.email, u.archive_frequency, u.archive_format
  FROM "user" u
 WHERE u.archive_frequency != 'N'
   AND u.email_valid = 'Y'
   AND NOT EXISTS (
       SELECT 1 FROM user_archive ua
        WHERE ua.user_id = u.id AND ua.status = 'S'
   );
```

## CloudWatch Logs Insights

The SES `message_id` is logged by `email_service.py` as structured JSON
but not stored in the database. Use CloudWatch Logs Insights to trace
delivery.

### Find SES message ID for a user's archive

```
# Log group: /aws/ecs/<project>-api  (or the archive task log group)
fields @timestamp, @message
| filter @message like "archive_email_sent"
| filter @message like "user_id"
| filter @message like /\"user_id\":\s*12345/
| sort @timestamp desc
| limit 20
```

### Find all archive email failures

```
fields @timestamp, @message
| filter @message like "archive_email_failed" or @message like "archive_email_error"
| sort @timestamp desc
| limit 50
```

### Trace a specific SES message

Once you have the `message_id` from the above query, look it up in the
SES event logs or use the AWS SES console "Message search" feature:

```bash
aws sesv2 get-message-insights --message-id "01020190..."
```

## Status codes

| Code | Meaning |
|------|---------|
| `S`  | Success -- archive generated and email sent |
| `F`  | Failed -- generation or send error (see `error_message`) |
| `K`  | Skipped -- reserved for future use (no new activity) |
