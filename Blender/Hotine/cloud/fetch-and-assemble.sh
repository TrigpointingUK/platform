#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_CONFIG="${SCRIPT_DIR}/spot-render.env"

usage() {
    cat <<'EOF'
Download rendered frames from S3 and assemble output locally.

Usage:
  bash cloud/fetch-and-assemble.sh --run-id RUN_ID [--config PATH] [--no-upload]
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

CONFIG_PATH="${DEFAULT_CONFIG}"
RUN_ID=""
UPLOAD_OUTPUT=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            shift 2
            ;;
        --no-upload)
            UPLOAD_OUTPUT=false
            shift
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

[[ -n "${RUN_ID}" ]] || die "--run-id is required"
[[ -f "${CONFIG_PATH}" ]] || die "Config not found: ${CONFIG_PATH}"
# shellcheck disable=SC1090
source "${CONFIG_PATH}"

AWS_REGION="${AWS_REGION:-}"
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-}"
RUNS_DIR="${RUNS_DIR:-${SCRIPT_DIR}/runs}"
TRIG_ANIMATION="${TRIG_ANIMATION:-flythrough}"
TRIG_RENDER_QUALITY="${TRIG_RENDER_QUALITY:-final}"
FPS="${FPS:-30}"
FRAME_JUMP="${FRAME_JUMP:-1}"

[[ -n "${AWS_REGION}" ]] || die "AWS_REGION missing in config"
[[ -n "${S3_BUCKET}" ]] || die "S3_BUCKET missing in config"
[[ -n "${S3_PREFIX}" ]] || die "S3_PREFIX missing in config"

RUN_DIR="${RUNS_DIR}/${RUN_ID}"
mkdir -p "${RUN_DIR}"

output_subdir="frames"
if [[ "${TRIG_ANIMATION}" == "bracket" ]]; then
    output_subdir="bracket"
elif [[ "${TRIG_RENDER_QUALITY}" == "draft" ]]; then
    output_subdir="draft"
elif [[ "${TRIG_RENDER_QUALITY}" == "final_4k" || "${TRIG_RENDER_QUALITY}" == "4k" || "${TRIG_RENDER_QUALITY}" == "uhd" ]]; then
    output_subdir="frames_4k"
fi

LOCAL_FRAMES_DIR="${RUN_DIR}/${output_subdir}"
mkdir -p "${LOCAL_FRAMES_DIR}"

FRAMES_S3_URI="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/frames/${output_subdir}/"
echo "Syncing frames from ${FRAMES_S3_URI}"
aws s3 sync \
    "${FRAMES_S3_URI}" \
    "${LOCAL_FRAMES_DIR}" \
    --region "${AWS_REGION}" \
    --exclude "*" \
    --include "*.png"

shopt -s nullglob
png_files=("${LOCAL_FRAMES_DIR}"/*.png)
frame_count="${#png_files[@]}"
shopt -u nullglob

if (( frame_count == 0 )); then
    die "No PNG frames found in ${LOCAL_FRAMES_DIR}"
fi

echo "Frames downloaded: ${frame_count}"

if [[ "${TRIG_ANIMATION}" == "bracket" ]]; then
    OUTPUT_FILE="${RUN_DIR}/bracket_orbit_${RUN_ID}.apng"
    ffmpeg -y \
        -framerate 24 \
        -i "${LOCAL_FRAMES_DIR}/%04d.png" \
        -vf "scale=iw/2:ih/2:flags=lanczos" \
        -plays 0 \
        -f apng \
        "${OUTPUT_FILE}"
else
    OUTPUT_FILE="${RUN_DIR}/trig_flythrough_${RUN_ID}.mp4"
    if (( FRAME_JUMP > 1 )); then
        INPUT_FPS=$(( FPS / FRAME_JUMP ))
        ffmpeg -y \
            -framerate "${INPUT_FPS}" \
            -pattern_type glob -i "${LOCAL_FRAMES_DIR}/*.png" \
            -c:v libx264 \
            -r "${FPS}" \
            -preset slow \
            -crf 18 \
            -pix_fmt yuv420p \
            -movflags +faststart \
            "${OUTPUT_FILE}"
    else
        ffmpeg -y \
            -framerate "${FPS}" \
            -i "${LOCAL_FRAMES_DIR}/%04d.png" \
            -c:v libx264 \
            -preset slow \
            -crf 18 \
            -pix_fmt yuv420p \
            -movflags +faststart \
            "${OUTPUT_FILE}"
    fi
fi

echo "Output assembled: ${OUTPUT_FILE}"

if [[ "${UPLOAD_OUTPUT}" == "true" ]]; then
    OUTPUT_S3_URI="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/output/$(basename "${OUTPUT_FILE}")"
    echo "Uploading output to ${OUTPUT_S3_URI}"
    aws s3 cp "${OUTPUT_FILE}" "${OUTPUT_S3_URI}" --region "${AWS_REGION}"
fi
