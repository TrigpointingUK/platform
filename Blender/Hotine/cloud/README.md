# Hotine Cloud Render Scripts

Spot-based Blender render tooling for the `Hotine` animation, using:

- ephemeral GPU EC2 workers (`one-time` Spot instances)
- S3 for source payload, frame checkpoints, logs, and final output
- local `ffmpeg` assembly on your workstation

Everything lives under `Blender/Hotine/cloud/` and does not touch Terraform.

## Files

- `spot-render.env.example` - configuration template
- `submit-spot-render.sh` - upload payload, shard frame ranges, launch workers
- `worker-bootstrap.sh` - worker entrypoint run by EC2 user-data
- `watch-spot-render.sh` - show EC2 state and S3 progress
- `fetch-and-assemble.sh` - download frames and build output locally
- `terminate-spot-render.sh` - terminate all worker instances for a run

## One-time setup

1. Copy config:
   - `cp cloud/spot-render.env.example cloud/spot-render.env`
2. Edit `cloud/spot-render.env` with your values:
   - AWS region, S3 bucket/prefix
   - GPU AMI ID (must include NVIDIA drivers, Debian/Ubuntu preferred)
   - subnet(s), security group(s), IAM instance profile name
   - swap sizing via `SWAP_GB` (default `32`, set `0` to disable)
   - periodic checkpoint sync via `FRAME_SYNC_INTERVAL_SEC` (default `30`)
   - optional quality override via `TRIG_RENDER_QUALITY`:
     `final`, `final_4k`, or `draft`
3. Ensure the instance profile can read/write:
   - `s3://<bucket>/<prefix>/<run-id>/*`

## Run a render

From `Blender/Hotine`:

1. Submit:
   - `bash cloud/submit-spot-render.sh`
   - resume an interrupted run with the same prefix:
     `bash cloud/submit-spot-render.sh --run-id <RUN_ID>`
2. Monitor:
   - `bash cloud/watch-spot-render.sh --run-id <RUN_ID>`
3. Fetch and assemble:
   - `bash cloud/fetch-and-assemble.sh --run-id <RUN_ID>`
4. Emergency stop (if needed):
   - `bash cloud/terminate-spot-render.sh --run-id <RUN_ID>`

`submit-spot-render.sh` prints the run ID and stores local state at:

- `cloud/runs/<RUN_ID>/`

## Notes

- Workers are configured as cattle:
  - Spot one-time instances
  - root volume only
  - root volume `DeleteOnTermination=true`
  - instance shutdown triggers termination
- Worker bootstrap installs Blender runtime libraries required for
  headless execution of the official Blender tarball.
- Launcher payload includes `res/TUK-Logo.svg` and sets `TRIG_RES_DIR`
  so flush-bracket logo relief imports consistently in cloud renders.
- Frames are uploaded to:
  - `s3://<bucket>/<prefix>/<RUN_ID>/frames/<subdir>/`
- Workers rehydrate existing frames from S3 before rendering, so reruns
  with the same run ID fill missing frames while preserving existing ones.
- Final local output goes to:
  - `cloud/runs/<RUN_ID>/`
- For capacity resilience, set multiple subnets using `SUBNET_IDS`.
  The launcher tries each subnet + instance-type combination.

## Recommended defaults for 4 workers

- `WORKER_COUNT="4"`
- `INSTANCE_TYPES="g5.xlarge g6.xlarge g4dn.xlarge"`
- `TOTAL_FRAMES="1788"` (flythrough default)

This gives mixed capacity options while staying on NVIDIA GPUs for Cycles.
