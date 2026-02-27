#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_CONFIG="${SCRIPT_DIR}/spot-render.env"

usage() {
    cat <<'EOF'
Show EC2 and S3 progress for a cloud render run.

Usage:
  bash cloud/watch-spot-render.sh --run-id RUN_ID [--config PATH]
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

CONFIG_PATH="${DEFAULT_CONFIG}"
RUN_ID=""

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
TOTAL_FRAMES="${TOTAL_FRAMES:-0}"

[[ -n "${AWS_REGION}" ]] || die "AWS_REGION missing in config"
[[ -n "${S3_BUCKET}" ]] || die "S3_BUCKET missing in config"
[[ -n "${S3_PREFIX}" ]] || die "S3_PREFIX missing in config"

RUN_DIR="${RUNS_DIR}/${RUN_ID}"
MANIFEST_FILE="${RUN_DIR}/instances.tsv"
mkdir -p "${RUN_DIR}"

if [[ ! -f "${MANIFEST_FILE}" ]]; then
    echo "Fetching manifest from S3 ..."
    aws s3 cp \
        "s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/meta/instances.tsv" \
        "${MANIFEST_FILE}" \
        --region "${AWS_REGION}"
fi

mapfile -t INSTANCE_IDS < <(awk 'NR > 1 {print $5}' "${MANIFEST_FILE}")
if [[ "${#INSTANCE_IDS[@]}" -eq 0 ]]; then
    die "No instance IDs found in ${MANIFEST_FILE}"
fi

echo
echo "Run ID: ${RUN_ID}"
echo "Instances: ${#INSTANCE_IDS[@]}"
echo

aws ec2 describe-instances \
    --region "${AWS_REGION}" \
    --instance-ids "${INSTANCE_IDS[@]}" \
    --query 'Reservations[].Instances[].{id:InstanceId,type:InstanceType,state:State.Name,az:Placement.AvailabilityZone,launch:LaunchTime}' \
    --output table

output_subdir="frames"
if [[ "${TRIG_ANIMATION}" == "bracket" ]]; then
    output_subdir="bracket"
elif [[ "${TRIG_RENDER_QUALITY}" == "draft" ]]; then
    output_subdir="draft"
elif [[ "${TRIG_RENDER_QUALITY}" == "final_4k" || "${TRIG_RENDER_QUALITY}" == "4k" || "${TRIG_RENDER_QUALITY}" == "uhd" ]]; then
    output_subdir="frames_4k"
fi

frames_prefix="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/frames/${output_subdir}/"
status_prefix="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/status/"
done_prefix="s3://${S3_BUCKET}/${S3_PREFIX}/${RUN_ID}/meta/shards/"

count_s3_objects() {
    local uri="$1"
    local recursive_flag="${2:-}"
    local ls_output=""
    if [[ "${recursive_flag}" == "recursive" ]]; then
        if ! ls_output="$(aws s3 ls "${uri}" --region "${AWS_REGION}" --recursive 2>/dev/null)"; then
            echo "0"
            return 0
        fi
    else
        if ! ls_output="$(aws s3 ls "${uri}" --region "${AWS_REGION}" 2>/dev/null)"; then
            echo "0"
            return 0
        fi
    fi
    printf "%s\n" "${ls_output}" | awk 'END{print NR + 0}'
}

print_status_payloads() {
    local ls_output=""
    if ! ls_output="$(aws s3 ls "${status_prefix}" --region "${AWS_REGION}" 2>/dev/null)"; then
        echo "  (none yet)"
        return 0
    fi

    if [[ -z "${ls_output}" ]]; then
        echo "  (none yet)"
        return 0
    fi

    while IFS= read -r line; do
        [[ -n "${line}" ]] || continue
        local key
        key="$(printf "%s\n" "${line}" | awk '{print $4}')"
        [[ -n "${key}" ]] || continue

        echo "  ${key}:"
        if ! aws s3 cp "${status_prefix}${key}" - --region "${AWS_REGION}" 2>/dev/null | sed 's/^/    /'; then
            echo "    (failed to fetch payload)"
        fi
    done <<< "${ls_output}"
}

frame_count="$(count_s3_objects "${frames_prefix}" recursive)"
status_count="$(count_s3_objects "${status_prefix}")"
done_count="$(count_s3_objects "${done_prefix}")"

echo
echo "S3 progress:"
echo "  Frames uploaded: ${frame_count}"
if (( TOTAL_FRAMES > 0 )); then
    echo "  Expected frames: ${TOTAL_FRAMES}"
fi
echo "  Status files:    ${status_count}"
echo "  Completed shards:${done_count}"
echo
echo "Shard status payloads:"
print_status_payloads
echo
echo "Useful commands:"
echo "  aws s3 ls ${frames_prefix} --recursive | tail"
echo "  aws s3 ls ${status_prefix}"
