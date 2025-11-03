#!/bin/bash
# Fix Valkey EFS permissions
# Run this on the bastion host

set -e

EFS_DNS="fs-03a85b954b54e214a.efs.eu-west-1.amazonaws.com"
MOUNT_POINT="/mnt/valkey-efs"

echo "Creating mount point..."
sudo mkdir -p "$MOUNT_POINT"

echo "Mounting EFS..."
sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport \
  "${EFS_DNS}:/" "$MOUNT_POINT"

echo "Current permissions:"
ls -la "$MOUNT_POINT/valkey-data"

echo "Fixing ownership to uid=999, gid=999 (valkey user)..."
sudo chown -R 999:999 "$MOUNT_POINT/valkey-data"

echo "New permissions:"
ls -la "$MOUNT_POINT/valkey-data"

echo "Unmounting..."
sudo umount "$MOUNT_POINT"

echo "Done! Valkey should now be able to write to /data"

