#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_CONFIG="${SCRIPT_DIR}/spot-render.env"

usage() {
    cat <<'EOF'
Terminate all EC2 instances for a submitted render run.

Usage:
  bash cloud/terminate-spot-render.sh --run-id RUN_ID [--config PATH]
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

echo "Terminating ${#INSTANCE_IDS[@]} instance(s) for run ${RUN_ID} ..."
aws ec2 terminate-instances \
    --region "${AWS_REGION}" \
    --instance-ids "${INSTANCE_IDS[@]}" \
    --query 'TerminatingInstances[].{id:InstanceId,old:PreviousState.Name,new:CurrentState.Name}' \
    --output table
