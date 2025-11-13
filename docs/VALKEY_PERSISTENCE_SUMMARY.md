# Valkey EFS Persistence Implementation - Summary

## What Was Changed

I've implemented persistent storage for your Valkey cache using Amazon EFS with RDB snapshots. This means your cache will now survive ECS task restarts and can warm up from recent snapshots.

## Files Modified

### Terraform Modules (`terraform/modules/valkey/`)
1. **main.tf** - Added:
   - EFS file system (encrypted, with 30-day IA lifecycle)
   - EFS mount targets in each AZ
   - EFS access point (uid/gid 1000)
   - EFS volume configuration in task definition
   - Updated Valkey command to enable RDB snapshots

2. **variables.tf** - Added:
   - `efs_security_group_id` variable

3. **outputs.tf** - Added:
   - `efs_file_system_id` output
   - `efs_access_point_id` output

### Terraform Common Infrastructure (`terraform/common/`)
4. **efs.tf** - Added:
   - Security group for Valkey EFS (allows NFS from Valkey tasks and bastion)

5. **valkey.tf** - Modified:
   - Added `efs_security_group_id` parameter to module call

6. **ecs.tf** - Modified:
   - Added EFS IAM permissions to task role

### Documentation
7. **docs/infrastructure/VALKEY_EFS_PERSISTENCE.md** - Created:
   - Complete implementation documentation
   - Deployment steps
   - Monitoring guidance
   - Troubleshooting guide

## Key Changes in Valkey Configuration

### Before (No Persistence)
```bash
--save ""  # Snapshots disabled
```

### After (With Persistence)
```bash
--dir /data                          # Store RDB files in EFS mount
--save "900 1 300 10 60 10000"       # Snapshot intervals
--dbfilename dump.rdb                # RDB filename
--rdbcompression yes                 # Compress snapshots
```

### Snapshot Schedule
- Save every **15 minutes** if at least 1 key changed
- Save every **5 minutes** if at least 10 keys changed
- Save every **1 minute** if at least 10,000 keys changed

## What Will Be Created

When you apply these changes:

1. **EFS File System** - `aws_efs_file_system.valkey`
   - Encrypted storage for RDB snapshots
   - Lifecycle policy (30 days to IA)
   
2. **EFS Mount Targets** - `aws_efs_mount_target.valkey[0-1]`
   - One in each availability zone
   
3. **EFS Access Point** - `aws_efs_access_point.valkey`
   - Manages permissions (uid=1000, gid=1000)
   
4. **EFS Security Group** - `aws_security_group.efs_valkey`
   - Allows NFS (port 2049) from Valkey tasks and bastion

## What Will Be Modified

1. **ECS Task Definition** - `aws_ecs_task_definition.valkey`
   - Adds EFS volume mount at `/data`
   - Updates Valkey command to enable persistence
   
2. **IAM Task Role Policy** - `aws_iam_role_policy.ecs_task_role_policy`
   - Adds EFS permissions (ClientMount, ClientWrite, ClientRootAccess)

## Next Steps

### 1. Review the Changes
```bash
cd terraform/common
terraform validate  # Already done ✓
terraform plan
```

### 2. Apply When Ready
```bash
terraform apply
```

**Important**: The current cache will be lost during this deployment since the old task had no persistence. After this change, future restarts will preserve cache data.

### 3. Verify After Deployment
```bash
# Wait for the new task to start, then test:
aws ecs list-tasks --cluster trigpointing-cluster --service-name trigpointing-valkey

# Set a test key via Redis Commander or CLI
# Then force a task restart
aws ecs update-service \
  --cluster trigpointing-cluster \
  --service trigpointing-valkey \
  --force-new-deployment

# After restart, verify the key persisted
```

## Benefits

✅ **Cache survives restarts** - RDB file persists in EFS
✅ **Faster recovery** - Warm cache on startup
✅ **Cost effective** - Only pay for actual storage (~$0.02-0.06/month)
✅ **Encrypted** - At rest and in transit
✅ **No manual backups** - Automatic RDB snapshots

## Cost Impact

- **EFS Storage**: ~10-50 MB = ~$0.01-0.05/month
- **EFS Requests**: Minimal = ~$0.01/month
- **Total**: ~$0.02-0.06/month additional

Much cheaper than ElastiCache Serverless (minimum $50+/month).

## Monitoring

After deployment, you can monitor:

1. **RDB Snapshots** - Via valkey-cli:
   ```bash
   redis-cli -h valkey.trigpointing.local INFO persistence
   ```

2. **CloudWatch Logs** - Check for:
   ```
   Background saving started
   DB saved on disk
   ```

3. **EFS Metrics** - CloudWatch > EFS > trigpointing-valkey-efs

## Documentation

Full documentation available at:
`docs/infrastructure/VALKEY_EFS_PERSISTENCE.md`

Includes:
- Architecture details
- Deployment steps
- Troubleshooting guide
- Tuning options
- Rollback procedures

