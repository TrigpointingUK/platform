# Valkey EFS Persistence Implementation

## Overview

This document describes the implementation of persistent storage for Valkey (Redis-compatible cache) using Amazon EFS (Elastic File System). This ensures cache data survives ECS task restarts and allows for warm cache recovery.

## Problem Statement

Previously, Valkey was configured with `--save ""` which disabled RDB (Redis Database) snapshots entirely. This meant:
- Every time the ECS task restarted, all cache data was lost
- Cache had to be rebuilt from scratch (cold start)
- No persistence across deployments

## Solution: EFS-Backed Persistence

We've implemented EFS-backed storage with RDB snapshots to provide:
- **Persistent storage** across task restarts
- **Automatic snapshots** at configurable intervals
- **Warm cache recovery** when tasks restart
- **Cost-effective** solution (minimal EFS storage needed)
- **Encrypted** data at rest and in transit

## Architecture Components

### 1. EFS File System
- **Location**: `terraform/modules/valkey/main.tf`
- Encrypted at rest
- General purpose performance mode
- Bursting throughput mode
- Lifecycle policy: transition to IA after 30 days

### 2. EFS Security Group
- **Location**: `terraform/common/efs.tf`
- Allows NFS (port 2049) from:
  - Valkey ECS tasks
  - Bastion host (for maintenance)

### 3. EFS Access Point
- **Location**: `terraform/modules/valkey/main.tf`
- Root directory: `/valkey-data`
- POSIX user: uid=1000, gid=1000
- Permissions: 755

### 4. EFS Mount in Task Definition
- **Location**: `terraform/modules/valkey/main.tf`
- Mounted at: `/data` in container
- Transit encryption: ENABLED
- IAM authorization: ENABLED

### 5. IAM Permissions
- **Location**: `terraform/common/ecs.tf`
- Added EFS permissions to ECS task role:
  - `elasticfilesystem:ClientMount`
  - `elasticfilesystem:ClientWrite`
  - `elasticfilesystem:ClientRootAccess`

## Valkey Configuration

### RDB Snapshot Settings

The Valkey container is now configured with the following persistence parameters:

```bash
--dir /data                          # Store RDB files in EFS mount
--save "900 1 300 10 60 10000"       # Snapshot intervals (see below)
--dbfilename dump.rdb                # RDB filename
--rdbcompression yes                 # Compress snapshots
--stop-writes-on-bgsave-error no     # Don't stop on save errors
```

### Snapshot Intervals Explained

The `--save` parameter uses the format: `<seconds> <changes>`

Current configuration:
- `900 1` - Save if at least **1 key** changed in 15 minutes
- `300 10` - Save if at least **10 keys** changed in 5 minutes
- `60 10000` - Save if at least **10,000 keys** changed in 1 minute

This balances:
- **Performance**: Not too frequent to impact operations
- **Data freshness**: Recent enough to avoid significant data loss
- **Storage**: Minimal disk I/O

## Files Modified

### Terraform Modules
1. **`terraform/modules/valkey/main.tf`**
   - Added EFS file system resource
   - Added EFS mount targets
   - Added EFS access point
   - Updated task definition with EFS volume
   - Updated Valkey container with persistence config

2. **`terraform/modules/valkey/variables.tf`**
   - Added `efs_security_group_id` variable

3. **`terraform/modules/valkey/outputs.tf`**
   - Added `efs_file_system_id` output
   - Added `efs_access_point_id` output

### Terraform Common Infrastructure
4. **`terraform/common/efs.tf`**
   - Added `aws_security_group.efs_valkey` resource

5. **`terraform/common/valkey.tf`**
   - Added `efs_security_group_id` parameter to module call

6. **`terraform/common/ecs.tf`**
   - Added EFS IAM permissions to task role policy

## Deployment Steps

### 1. Review Changes
```bash
cd terraform/common
terraform plan
```

Expected new resources:
- `aws_efs_file_system.valkey` (in module)
- `aws_efs_mount_target.valkey[0]` (in module)
- `aws_efs_mount_target.valkey[1]` (in module)
- `aws_efs_access_point.valkey` (in module)
- `aws_security_group.efs_valkey`

Expected modified resources:
- `aws_ecs_task_definition.valkey` (in module)
- `aws_iam_role_policy.ecs_task_role_policy`

### 2. Apply Infrastructure Changes
```bash
cd terraform/common
terraform apply
```

This will:
1. Create the EFS file system
2. Create mount targets in each AZ
3. Create the EFS access point
4. Update the task definition with volume mount
5. Update IAM permissions

### 3. Deploy New Task
The ECS service will automatically:
1. Register the new task definition
2. Stop the old task
3. Start a new task with EFS mounted

**Note**: Current cache will be lost during this initial transition since the old task had no persistence.

### 4. Verify Persistence

After deployment, test persistence:

```bash
# 1. Connect to bastion
ssh bastion

# 2. Connect to Valkey via Redis Commander or valkey-cli
# Set some test keys
redis-cli -h valkey.trigpointing.local SET test_key "test_value"

# 3. Restart the ECS task
aws ecs update-service \
  --cluster trigpointing-cluster \
  --service trigpointing-valkey \
  --force-new-deployment

# 4. Wait for new task to start, then verify data persisted
redis-cli -h valkey.trigpointing.local GET test_key
# Should return: "test_value"
```

## Benefits

### 1. Cache Warm-Up on Restart
When the Valkey task restarts:
- Loads `dump.rdb` from EFS automatically
- Cache is pre-populated with recent data
- Reduces cold start impact

### 2. Deployment Resilience
- Blue/green deployments can reference the same EFS
- Rolling updates preserve cache state
- Reduced latency after deployments

### 3. Data Safety
- Automatic periodic backups (RDB snapshots)
- Encrypted at rest (EFS)
- Encrypted in transit (TLS)

### 4. Cost Effective
- EFS bursting mode is cost-effective for small workloads
- Only pay for actual data stored
- IA lifecycle policy reduces costs for older data

## Monitoring

### Check RDB Snapshot Status

Connect to Valkey and check:

```bash
# Via valkey-cli
redis-cli -h valkey.trigpointing.local INFO persistence
```

Look for:
- `rdb_last_save_time`: Timestamp of last successful save
- `rdb_changes_since_last_save`: Number of changes since last save
- `rdb_last_bgsave_status`: Status of last background save

### CloudWatch Logs

Monitor Valkey logs for:
```
Background saving started by pid <pid>
DB saved on disk
```

### EFS Metrics

Monitor in CloudWatch:
- EFS > File Systems > `trigpointing-valkey-efs`
- Check: Burst credit balance, throughput, I/O operations

## Rollback Plan

If issues arise:

### Option 1: Disable Persistence (Revert)
```bash
cd terraform/modules/valkey
git revert <commit-hash>
terraform apply
```

### Option 2: Disable Snapshots Only
Change `--save "900 1 300 10 60 10000"` back to `--save ""` in `main.tf`, then:
```bash
terraform apply
```

The EFS volume will remain mounted but no snapshots will be taken.

## Tuning

### Adjust Snapshot Frequency

Edit `terraform/modules/valkey/main.tf`, line ~114:

**More frequent** (higher I/O, better recovery):
```bash
--save "300 1 60 10 10 10000"  # 5min/1key, 1min/10keys, 10sec/10000keys
```

**Less frequent** (lower I/O, more data loss risk):
```bash
--save "3600 1 900 10 300 10000"  # 1hour/1key, 15min/10keys, 5min/10000keys
```

**Current (balanced)**:
```bash
--save "900 1 300 10 60 10000"  # 15min/1key, 5min/10keys, 1min/10000keys
```

## Troubleshooting

### Issue: Task fails to start with EFS mount error

**Symptoms**: Task stops immediately, logs show EFS mount failure

**Causes**:
1. IAM permissions not propagated
2. Security group rules not allowing NFS traffic
3. EFS mount targets not ready

**Solutions**:
```bash
# Check IAM policy
aws iam get-role-policy \
  --role-name trigpointing-ecs-task-role \
  --policy-name trigpointing-ecs-task-policy

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids <efs-valkey-sg-id>

# Check EFS mount targets
aws efs describe-mount-targets \
  --file-system-id <fs-id>
```

### Issue: RDB snapshots failing

**Symptoms**: Logs show "Background saving error"

**Check**:
1. EFS disk space (unlikely with cache size)
2. Write permissions on `/data`
3. Memory pressure during fork

**Solutions**:
```bash
# Connect to task via ECS Exec
aws ecs execute-command \
  --cluster trigpointing-cluster \
  --task <task-id> \
  --container valkey \
  --interactive \
  --command "/bin/sh"

# Check directory permissions
ls -la /data

# Check memory usage
redis-cli INFO memory
```

### Issue: Old dump.rdb prevents startup

**Symptoms**: Task unhealthy, logs show RDB load errors

**Solution**: Clear the corrupted RDB file
```bash
# From bastion, mount EFS and remove bad file
sudo mount -t nfs4 -o nfsvers=4.1 \
  <efs-dns-name>:/ /mnt/valkey
sudo rm /mnt/valkey/valkey-data/dump.rdb
```

## Cost Estimation

Based on current usage patterns:

- **EFS Storage**: ~10-50 MB cache data = ~$0.01-0.05/month
- **EFS Requests**: Minimal (background saves) = ~$0.01/month
- **Total additional cost**: ~$0.02-0.06/month

Much cheaper than ElastiCache Serverless (minimum $50+/month).

## Future Enhancements

Potential improvements:
1. **AOF (Append Only File)**: More durable but slower
2. **Backup automation**: EFS backups for disaster recovery
3. **Multi-AZ EFS**: Automatic failover (currently single region)
4. **Monitoring alerts**: Alert on failed RDB saves

## References

- [Valkey Documentation](https://valkey.io/docs/)
- [Redis Persistence Documentation](https://redis.io/docs/management/persistence/)
- [AWS EFS with ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efs-volumes.html)
- [ECS Task IAM Roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)

