#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_CONFIG="${SCRIPT_DIR}/spot-render.env"

usage() {
    cat <<'EOF'
Launch sharded Blender renders on Spot GPU instances.

Usage:
  bash cloud/submit-spot-render.sh [--config PATH] [--run-id RUN_ID]

Notes:
  - Copy cloud/spot-render.env.example to cloud/spot-render.env first.
  - This script uploads a source payload to S3, then launches one Spot
    instance per shard.
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

require_var() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        die "Missing required config variable: ${name}"
    fi
}

CONFIG_PATH="${DEFAULT_CONFIG}"
RUN_ID_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID_OVERRIDE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown argument: $1"
            ;;
    esac
done

[[ -f "${CONFIG_PATH}" ]] || die "Config not found: ${CONFIG_PATH}"
# shellcheck disable=SC1090
source "${CONFIG_PATH}"

require_var AWS_REGION
require_var S3_BUCKET
require_var S3_PREFIX
require_var AMI_ID
require_var INSTANCE_PROFILE_NAME
require_var HOTINE_DIR

SUBNETS_RAW="${SUBNET_IDS:-${SUBNET_ID:-}}"
[[ -n "${SUBNETS_RAW}" ]] || die "Set SUBNET_ID or SUBNET_IDS in config"
read -r -a SUBNET_ARRAY <<< "${SUBNETS_RAW//,/ }"
[[ "${#SUBNET_ARRAY[@]}" -gt 0 ]] || die "No valid subnet IDs found"

SECURITY_GROUPS_RAW="${SECURITY_GROUP_IDS:-${SECURITY_GROUP_ID:-}}"
[[ -n "${SECURITY_GROUPS_RAW}" ]] || die "Set SECURITY_GROUP_ID or SECURITY_GROUP_IDS in config"

read -r -a SECURITY_GROUPS <<< "${SECURITY_GROUPS_RAW//,/ }"
[[ "${#SECURITY_GROUPS[@]}" -gt 0 ]] || die "No valid security group IDs found"

read -r -a INSTANCE_TYPE_ARRAY <<< "${INSTANCE_TYPES:-}"
[[ "${#INSTANCE_TYPE_ARRAY[@]}" -gt 0 ]] || die "INSTANCE_TYPES must include at least one type"

WORKER_COUNT="${WORKER_COUNT:-4}"
TOTAL_FRAMES="${TOTAL_FRAMES:-1788}"
ROOT_VOLUME_GB="${ROOT_VOLUME_GB:-120}"
SWAP_GB="${SWAP_GB:-32}"
FRAME_SYNC_INTERVAL_SEC="${FRAME_SYNC_INTERVAL_SEC:-30}"
FRAME_JUMP="${FRAME_JUMP:-1}"
TRIG_ANIMATION="${TRIG_ANIMATION:-flythrough}"
TRIG_RENDER_QUALITY="${TRIG_RENDER_QUALITY:-final}"
RUNS_DIR="${RUNS_DIR:-${SCRIPT_DIR}/runs}"

if (( WORKER_COUNT < 1 )); then
    die "WORKER_COUNT must be >= 1"
fi
if (( TOTAL_FRAMES < 1 )); then
    die "TOTAL_FRAMES must be >= 1"
fi
if ! [[ "${FRAME_SYNC_INTERVAL_SEC}" =~ ^[0-9]+$ ]]; then
    die "FRAME_SYNC_INTERVAL_SEC must be a non-negative integer"
fi
if (( WORKER_COUNT > TOTAL_FRAMES )); then
    echo "WORKER_COUNT (${WORKER_COUNT}) > TOTAL_FRAMES (${TOTAL_FRAMES}); reducing workers." >&2
    WORKER_COUNT="${TOTAL_FRAMES}"
fi

RUN_ID="${RUN_ID_OVERRIDE:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_DIR="${RUNS_DIR}/${RUN_ID}"
mkdir -p "${RUN_DIR}"

HOTINE_DIR="$(cd "${HOTINE_DIR}" && pwd)"
[[ -d "${HOTINE_DIR}" ]] || die "HOTINE_DIR is not a directory: ${HOTINE_DIR}"
PROJECT_PARENT="$(dirname "${HOTINE_DIR}")"
PROJECT_ROOT="$(dirname "${PROJECT_PARENT}")"
HOTINE_NAME="$(basename "${HOTINE_DIR}")"
LOGO_REL_PATH="res/TUK-Logo.svg"
LOGO_ABS_PATH="${PROJECT_ROOT}/${LOGO_REL_PATH}"

PAYLOAD_FILE="${RUN_DIR}/hotine-input.tar.gz"
INPUT_S3_URI="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/input/hotine-input.tar.gz"
META_S3_PREFIX="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/meta"

echo "Creating payload: ${PAYLOAD_FILE}"
tar_args=(
    --exclude="${HOTINE_NAME}/cloud/runs/*"
    --exclude="${HOTINE_NAME}/frames/*"
    --exclude="${HOTINE_NAME}/frames_4k/*"
    --exclude="${HOTINE_NAME}/draft/*"
    --exclude="${HOTINE_NAME}/preview/*"
    --exclude="${HOTINE_NAME}/bracket/*"
    --exclude="${HOTINE_NAME}/trig_flythrough.mp4"
    --exclude="${HOTINE_NAME}/trig_flythrough_4k.mp4"
    --exclude="${HOTINE_NAME}/trig_preview.mp4"
    --exclude="${HOTINE_NAME}/trig_draft.mp4"
    --exclude="${HOTINE_NAME}/bracket_orbit.apng"
    -C "${PROJECT_PARENT}" "${HOTINE_NAME}"
)
if [[ -f "${LOGO_ABS_PATH}" ]]; then
    tar_args+=(-C "${PROJECT_ROOT}" "${LOGO_REL_PATH}")
else
    echo "WARNING: ${LOGO_ABS_PATH} not found; cloud logo import may be skipped." >&2
fi
tar -czf "${PAYLOAD_FILE}" "${tar_args[@]}"

echo "Uploading payload to ${INPUT_S3_URI}"
aws s3 cp "${PAYLOAD_FILE}" "${INPUT_S3_URI}" --region "${AWS_REGION}"

MANIFEST_FILE="${RUN_DIR}/instances.tsv"
cat > "${MANIFEST_FILE}" <<'EOF'
shard	frame_start	frame_end	instance_type	instance_id	subnet_id
EOF

cat > "${RUN_DIR}/run.env" <<EOF
RUN_ID="${RUN_ID}"
AWS_REGION="${AWS_REGION}"
S3_BUCKET="${S3_BUCKET}"
S3_PREFIX="${S3_PREFIX}"
TOTAL_FRAMES="${TOTAL_FRAMES}"
WORKER_COUNT="${WORKER_COUNT}"
TRIG_ANIMATION="${TRIG_ANIMATION}"
TRIG_RENDER_QUALITY="${TRIG_RENDER_QUALITY}"
FRAME_JUMP="${FRAME_JUMP}"
SWAP_GB="${SWAP_GB}"
FRAME_SYNC_INTERVAL_SEC="${FRAME_SYNC_INTERVAL_SEC}"
EOF

spot_options="MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}"
if [[ -n "${SPOT_MAX_PRICE:-}" ]]; then
    spot_options="MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate,MaxPrice=${SPOT_MAX_PRICE}}"
fi

base_chunk=$(( TOTAL_FRAMES / WORKER_COUNT ))
remainder=$(( TOTAL_FRAMES % WORKER_COUNT ))
frame_start=1

launch_one_shard() {
    local shard="$1"
    local start="$2"
    local end="$3"
    local chosen_type=""
    local instance_id=""
    local chosen_subnet=""

    local user_data_file="${RUN_DIR}/user-data-shard-${shard}.sh"
    cat > "${user_data_file}" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export AWS_REGION='${AWS_REGION}'
export S3_BUCKET='${S3_BUCKET}'
export S3_PREFIX='${S3_PREFIX}'
export RUN_ID='${RUN_ID}'
export SHARD_INDEX='${shard}'
export FRAME_START='${start}'
export FRAME_END='${end}'
export FRAME_JUMP='${FRAME_JUMP}'
export TRIG_ANIMATION='${TRIG_ANIMATION}'
export TRIG_RENDER_QUALITY='${TRIG_RENDER_QUALITY}'
export TRIG_HIDE_TERRAIN='${TRIG_HIDE_TERRAIN:-}'
export TRIG_RES_DIR='/tmp/hotine-work/res'
export SWAP_GB='${SWAP_GB}'
export FRAME_SYNC_INTERVAL_SEC='${FRAME_SYNC_INTERVAL_SEC}'
export BLENDER_ARCHIVE='${BLENDER_ARCHIVE:-blender-4.3.2-linux-x64.tar.xz}'
export BLENDER_DOWNLOAD_URL='${BLENDER_DOWNLOAD_URL:-https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz}'

wait_for_apt_lock() {
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 \
           21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 \
           41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do
    if ! pgrep -x apt >/dev/null 2>&1 && \
       ! pgrep -x apt-get >/dev/null 2>&1 && \
       ! pgrep -x dpkg >/dev/null 2>&1 && \
       ! pgrep -f unattended-upgrade >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

install_aws_cli_if_missing() {
  if command -v aws >/dev/null 2>&1; then
    return 0
  fi

  wait_for_apt_lock || true
  for _ in 1 2 3 4 5 6; do
    if apt-get update -y; then
      break
    fi
    sleep 5
  done

  wait_for_apt_lock || true
  for _ in 1 2 3 4 5 6; do
    if apt-get install -y --no-install-recommends awscli ca-certificates curl tar xz-utils; then
      break
    fi
    sleep 5
  done

  command -v aws >/dev/null 2>&1
}

export DEBIAN_FRONTEND=noninteractive
dpkg --configure -a || true
install_aws_cli_if_missing || {
  echo "ERROR: aws CLI unavailable after retries"
  exit 1
}

mkdir -p /tmp/hotine-work
aws s3 cp \
  "s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/input/hotine-input.tar.gz" \
  "/tmp/hotine-work/hotine-input.tar.gz" \
  --region "${AWS_REGION}"
tar -xzf "/tmp/hotine-work/hotine-input.tar.gz" -C "/tmp/hotine-work"

bash "/tmp/hotine-work/Hotine/cloud/worker-bootstrap.sh"
EOF

    local type_count="${#INSTANCE_TYPE_ARRAY[@]}"
    local subnet_count="${#SUBNET_ARRAY[@]}"

    for ((subnet_attempt = 0; subnet_attempt < subnet_count; subnet_attempt++)); do
        local subnet_idx=$(( (shard - 1 + subnet_attempt) % subnet_count ))
        local candidate_subnet="${SUBNET_ARRAY[$subnet_idx]}"

        for ((type_attempt = 0; type_attempt < type_count; type_attempt++)); do
            local type_idx=$(( (shard - 1 + type_attempt) % type_count ))
            local candidate="${INSTANCE_TYPE_ARRAY[$type_idx]}"
            local instance_tag_spec="ResourceType=instance,Tags=[{Key=Name,Value=hotine-${RUN_ID}-s$(printf '%02d' "${shard}")},{Key=Project,Value=HotineRender},{Key=RunId,Value=${RUN_ID}},{Key=Shard,Value=${shard}},{Key=ManagedBy,Value=submit-spot-render.sh}]"
            local volume_tag_spec="ResourceType=volume,Tags=[{Key=Project,Value=HotineRender},{Key=RunId,Value=${RUN_ID}},{Key=Shard,Value=${shard}},{Key=ManagedBy,Value=submit-spot-render.sh}]"

            local -a launch_cmd
            launch_cmd=(
                aws ec2 run-instances
                --region "${AWS_REGION}"
                --image-id "${AMI_ID}"
                --instance-type "${candidate}"
                --count 1
                --instance-market-options "${spot_options}"
                --instance-initiated-shutdown-behavior terminate
                --iam-instance-profile "Name=${INSTANCE_PROFILE_NAME}"
                --subnet-id "${candidate_subnet}"
                --security-group-ids
            )
            for sg in "${SECURITY_GROUPS[@]}"; do
                launch_cmd+=("${sg}")
            done
            launch_cmd+=(
                --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":${ROOT_VOLUME_GB},\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true}}]"
                --user-data "file://${user_data_file}"
                --tag-specifications "${instance_tag_spec}" "${volume_tag_spec}"
            )
            if [[ -n "${KEY_NAME:-}" ]]; then
                launch_cmd+=(--key-name "${KEY_NAME}")
            fi

            echo "Launching shard ${shard} (${start}-${end}) on ${candidate} in ${candidate_subnet} ..."
            if instance_id="$("${launch_cmd[@]}" --query 'Instances[0].InstanceId' --output text)"; then
                chosen_type="${candidate}"
                chosen_subnet="${candidate_subnet}"
                break 2
            fi
            echo "  Launch failed on ${candidate} in ${candidate_subnet}; trying next option." >&2
        done
    done

    if [[ -z "${instance_id}" || "${instance_id}" == "None" ]]; then
        return 1
    fi

    printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
        "${shard}" "${start}" "${end}" "${chosen_type}" "${instance_id}" "${chosen_subnet}" \
        >> "${MANIFEST_FILE}"
    echo "  -> shard ${shard} instance: ${instance_id} (${chosen_type}, ${chosen_subnet})"
    return 0
}

for ((shard = 1; shard <= WORKER_COUNT; shard++)); do
    chunk_size="${base_chunk}"
    if (( shard <= remainder )); then
        chunk_size=$(( chunk_size + 1 ))
    fi
    frame_end=$(( frame_start + chunk_size - 1 ))
    if (( frame_end > TOTAL_FRAMES )); then
        frame_end="${TOTAL_FRAMES}"
    fi

    launch_one_shard "${shard}" "${frame_start}" "${frame_end}" || die "Failed to launch shard ${shard}"

    frame_start=$(( frame_end + 1 ))
done

aws s3 cp "${MANIFEST_FILE}" "${META_S3_PREFIX}/instances.tsv" --region "${AWS_REGION}"
aws s3 cp "${RUN_DIR}/run.env" "${META_S3_PREFIX}/run.env" --region "${AWS_REGION}"

echo
echo "Run submitted successfully."
echo "Run ID: ${RUN_ID}"
echo "Local run dir: ${RUN_DIR}"
echo "Manifest: ${MANIFEST_FILE}"
echo
echo "Next steps:"
echo "  bash cloud/watch-spot-render.sh --config ${CONFIG_PATH} --run-id ${RUN_ID}"
echo "  bash cloud/fetch-and-assemble.sh --config ${CONFIG_PATH} --run-id ${RUN_ID}"
