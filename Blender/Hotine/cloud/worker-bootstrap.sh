#!/usr/bin/env bash
set -euo pipefail

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
    echo "[$(timestamp)] $*"
}

die() {
    log "ERROR: $*"
    exit 1
}

require_var() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        die "Missing required environment variable: ${name}"
    fi
}

publish_status() {
    local status="$1"
    local message="$2"
    local status_file
    status_file="$(mktemp)"
    cat > "${status_file}" <<EOF
{
  "run_id": "${RUN_ID}",
  "shard": ${SHARD_INDEX},
  "status": "${status}",
  "message": "${message}",
  "frame_start": ${FRAME_START},
  "frame_end": ${FRAME_END},
  "timestamp_utc": "$(timestamp)"
}
EOF

    aws s3 cp \
        "${status_file}" \
        "s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/status/shard-$(printf '%02d' "${SHARD_INDEX}").json" \
        --region "${AWS_REGION}" \
        --only-show-errors || true
    rm -f "${status_file}"
}

SYNC_LOOP_PID=""

stop_sync_loop() {
    if [[ -n "${SYNC_LOOP_PID}" ]] && kill -0 "${SYNC_LOOP_PID}" 2>/dev/null; then
        kill "${SYNC_LOOP_PID}" >/dev/null 2>&1 || true
        wait "${SYNC_LOOP_PID}" 2>/dev/null || true
    fi
    SYNC_LOOP_PID=""
}

cleanup() {
    stop_sync_loop
}

on_error() {
    local line="$1"
    local code="$2"
    publish_status "failed" "worker failed at line ${line} with exit code ${code}"
    exit "${code}"
}

trap cleanup EXIT
trap 'on_error "${LINENO}" "$?"' ERR

require_var AWS_REGION
require_var S3_BUCKET
require_var S3_PREFIX
require_var RUN_ID
require_var SHARD_INDEX
require_var FRAME_START
require_var FRAME_END
require_var TRIG_ANIMATION
require_var TRIG_RENDER_QUALITY
require_var BLENDER_ARCHIVE
require_var BLENDER_DOWNLOAD_URL

FRAME_JUMP="${FRAME_JUMP:-1}"
TRIG_HIDE_TERRAIN="${TRIG_HIDE_TERRAIN:-}"
SWAP_GB="${SWAP_GB:-32}"
SWAP_FILE="/swapfile-hotine"
FRAME_SYNC_INTERVAL_SEC="${FRAME_SYNC_INTERVAL_SEC:-30}"

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

install_dependencies() {
    wait_for_apt_lock || true
    dpkg --configure -a || true

    for _ in 1 2 3 4 5 6; do
        if apt-get update -y; then
            break
        fi
        sleep 5
    done

    wait_for_apt_lock || true
    for _ in 1 2 3 4 5 6; do
        if apt-get install -y --no-install-recommends \
            awscli ca-certificates curl tar xz-utils \
            libgl1 libsm6 libxext6 libxfixes3 libxi6 libxkbcommon0 libxrandr2 libxrender1 libxxf86vm1; then
            break
        fi
        sleep 5
    done

    command -v aws >/dev/null 2>&1 || die "aws CLI unavailable after retries"
}

ensure_swap() {
    if (( SWAP_GB <= 0 )); then
        log "Swap disabled (SWAP_GB=${SWAP_GB})"
        return 0
    fi

    if [[ -n "$(swapon --show=NAME --noheadings 2>/dev/null || true)" ]]; then
        log "Swap already enabled; leaving existing swap configuration in place."
        return 0
    fi

    log "Creating ${SWAP_GB}G swap file at ${SWAP_FILE}"
    rm -f "${SWAP_FILE}"
    if ! fallocate -l "${SWAP_GB}G" "${SWAP_FILE}" 2>/dev/null; then
        dd if=/dev/zero of="${SWAP_FILE}" bs=1M count="$((SWAP_GB * 1024))" status=none
    fi
    chmod 600 "${SWAP_FILE}"
    mkswap "${SWAP_FILE}" >/dev/null
    swapon "${SWAP_FILE}"
    log "Swap enabled."
}

count_local_frames() {
    shopt -s nullglob
    local files=("${HOTINE_DIR}/${output_subdir}"/*.png)
    local count="${#files[@]}"
    shopt -u nullglob
    echo "${count}"
}

sync_frames_to_s3() {
    aws s3 sync \
        "${HOTINE_DIR}/${output_subdir}/" \
        "${FRAMES_S3_URI}" \
        --region "${AWS_REGION}" \
        --exclude "*" \
        --include "*.png" \
        --only-show-errors
}

sync_existing_frames_from_s3() {
    log "Rehydrating existing frames from ${FRAMES_S3_URI}"
    sync_frames_from_s3_cmd=(
        aws s3 sync
        "${FRAMES_S3_URI}"
        "${HOTINE_DIR}/${output_subdir}/"
        --region "${AWS_REGION}"
        --exclude "*"
        --include "*.png"
        --only-show-errors
    )
    "${sync_frames_from_s3_cmd[@]}"
}

start_periodic_sync_loop() {
    local render_pid="$1"
    if (( FRAME_SYNC_INTERVAL_SEC <= 0 )); then
        log "Periodic frame sync disabled (FRAME_SYNC_INTERVAL_SEC=${FRAME_SYNC_INTERVAL_SEC})"
        return 0
    fi

    (
        while kill -0 "${render_pid}" 2>/dev/null; do
            sleep "${FRAME_SYNC_INTERVAL_SEC}"
            if ! kill -0 "${render_pid}" 2>/dev/null; then
                break
            fi
            if sync_frames_to_s3; then
                local_count="$(count_local_frames)"
                publish_status "rendering" "render running, local frames: ${local_count}"
                log "Periodic frame sync complete (${local_count} local frames)"
            else
                log "WARNING: periodic frame sync failed; will retry."
            fi
        done
    ) &
    SYNC_LOOP_PID="$!"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOTINE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="/var/log/hotine-worker.log"

mkdir -p "$(dirname "${LOG_FILE}")"
exec > >(tee -a "${LOG_FILE}") 2>&1

publish_status "starting" "bootstrapping shard worker"
log "Run: ${RUN_ID} shard ${SHARD_INDEX} frames ${FRAME_START}-${FRAME_END}"

export DEBIAN_FRONTEND=noninteractive
install_dependencies
ensure_swap

if ! command -v nvidia-smi >/dev/null 2>&1; then
    die "nvidia-smi not found; use a GPU AMI with NVIDIA drivers pre-installed"
fi
nvidia-smi || die "GPU is not ready"

BLENDER_INSTALL_ROOT="/opt/blender"
mkdir -p "${BLENDER_INSTALL_ROOT}"
BLENDER_ARCHIVE_PATH="${BLENDER_INSTALL_ROOT}/${BLENDER_ARCHIVE}"
BLENDER_DIR_NAME="${BLENDER_ARCHIVE%.tar.xz}"
BLENDER_DIR="${BLENDER_INSTALL_ROOT}/${BLENDER_DIR_NAME}"
BLENDER_BIN="${BLENDER_DIR}/blender"

if [[ ! -x "${BLENDER_BIN}" ]]; then
    log "Downloading Blender: ${BLENDER_DOWNLOAD_URL}"
    curl -fsSL --retry 5 --retry-delay 3 "${BLENDER_DOWNLOAD_URL}" -o "${BLENDER_ARCHIVE_PATH}"
    tar -xf "${BLENDER_ARCHIVE_PATH}" -C "${BLENDER_INSTALL_ROOT}"
fi
[[ -x "${BLENDER_BIN}" ]] || die "Blender binary not found at ${BLENDER_BIN}"

output_subdir="frames"
if [[ "${TRIG_ANIMATION}" == "bracket" ]]; then
    output_subdir="bracket"
elif [[ "${TRIG_RENDER_QUALITY}" == "draft" ]]; then
    output_subdir="draft"
elif [[ "${TRIG_RENDER_QUALITY}" == "final_4k" || "${TRIG_RENDER_QUALITY}" == "4k" || "${TRIG_RENDER_QUALITY}" == "uhd" ]]; then
    output_subdir="frames_4k"
fi

FRAMES_S3_URI="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/frames/${output_subdir}/"

mkdir -p "${HOTINE_DIR}/${output_subdir}"

export TRIG_ANIMATION
export TRIG_RENDER_QUALITY
if [[ -n "${TRIG_HIDE_TERRAIN}" ]]; then
    export TRIG_HIDE_TERRAIN
fi

publish_status "rehydrating" "syncing existing frames from S3"
sync_existing_frames_from_s3
rehydrated_count="$(count_local_frames)"
log "Rehydrated ${rehydrated_count} frame(s) from S3."

publish_status "rendering" "render started (existing frames: ${rehydrated_count})"
log "Starting render with ${BLENDER_BIN}"

render_cmd=(
    "${BLENDER_BIN}" --background
    --python "${HOTINE_DIR}/trig_pillar.py"
)
if (( FRAME_JUMP > 1 )); then
    render_cmd+=(--frame-jump "${FRAME_JUMP}")
fi
render_cmd+=(
    --frame-start "${FRAME_START}"
    --frame-end "${FRAME_END}"
    --render-anim
)

render_start_epoch="$(date +%s)"
"${render_cmd[@]}" &
render_pid="$!"
start_periodic_sync_loop "${render_pid}"
wait "${render_pid}"
stop_sync_loop
render_elapsed=$(( $(date +%s) - render_start_epoch ))
log "Render completed in ${render_elapsed}s"

publish_status "syncing" "uploading rendered frames to S3"
sync_frames_to_s3
final_count="$(count_local_frames)"
log "Final frame sync complete (${final_count} local frames)"

SHARD_META_FILE="$(mktemp)"
cat > "${SHARD_META_FILE}" <<EOF
run_id=${RUN_ID}
shard=${SHARD_INDEX}
frame_start=${FRAME_START}
frame_end=${FRAME_END}
frame_jump=${FRAME_JUMP}
animation=${TRIG_ANIMATION}
quality=${TRIG_RENDER_QUALITY}
completed_utc=$(timestamp)
EOF

aws s3 cp \
    "${LOG_FILE}" \
    "s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/logs/shard-$(printf '%02d' "${SHARD_INDEX}").log" \
    --region "${AWS_REGION}" \
    --only-show-errors || true

aws s3 cp \
    "${SHARD_META_FILE}" \
    "s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/meta/shards/shard-$(printf '%02d' "${SHARD_INDEX}").done" \
    --region "${AWS_REGION}" \
    --only-show-errors

rm -f "${SHARD_META_FILE}"

publish_status "completed" "render and sync completed"
log "Shard complete; requesting instance shutdown for termination."
shutdown -h now || poweroff || true
