#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_INPUT="${SCRIPT_DIR}/trig_flythrough_20260227T130329Z.mp4"
DEFAULT_OUTPUT_ROOT="${SCRIPT_DIR}/hls"

usage() {
    cat <<'EOF'
Package a 4K MP4 into a multi-resolution HLS ladder for S3 delivery.

Usage:
  bash Blender/Hotine/build-hls-ladder.sh [options]

Options:
  --input PATH              Input MP4 file (default: trig_flythrough_20260227T130329Z.mp4)
  --output-dir PATH         Output directory (default: Blender/Hotine/hls/<input-basename>/)
  --segment-duration SEC    HLS segment length in seconds (default: 6)
  --force                   Remove output directory if it already exists
  -h, --help                Show this help

Output structure:
  <output-dir>/master.m3u8
  <output-dir>/<variant>/index.m3u8
  <output-dir>/<variant>/segment_00000.ts
  ...
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

require_cmd() {
    local cmd="$1"
    command -v "${cmd}" >/dev/null 2>&1 || die "Required command not found: ${cmd}"
}

INPUT_FILE="${DEFAULT_INPUT}"
OUTPUT_DIR=""
SEGMENT_DURATION=6
FORCE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input)
            INPUT_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --segment-duration)
            SEGMENT_DURATION="$2"
            shift 2
            ;;
        --force)
            FORCE=true
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

require_cmd ffmpeg
require_cmd ffprobe

[[ -f "${INPUT_FILE}" ]] || die "Input file not found: ${INPUT_FILE}"
[[ "${SEGMENT_DURATION}" =~ ^[0-9]+$ ]] || die "--segment-duration must be a positive integer"
(( SEGMENT_DURATION > 0 )) || die "--segment-duration must be greater than 0"

if [[ -z "${OUTPUT_DIR}" ]]; then
    input_basename="$(basename "${INPUT_FILE}")"
    input_stem="${input_basename%.*}"
    OUTPUT_DIR="${DEFAULT_OUTPUT_ROOT}/${input_stem}"
fi

if [[ -d "${OUTPUT_DIR}" ]]; then
    if [[ "${FORCE}" != "true" ]]; then
        die "Output directory already exists: ${OUTPUT_DIR} (use --force to replace)"
    fi
    rm -rf "${OUTPUT_DIR}"
fi
mkdir -p "${OUTPUT_DIR}"

source_height="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=nokey=1:noprint_wrappers=1 "${INPUT_FILE}")"
[[ "${source_height}" =~ ^[0-9]+$ ]] || die "Could not determine input video height"

audio_stream_count="$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "${INPUT_FILE}" | wc -l | tr -d ' ')"
has_audio=false
if (( audio_stream_count > 0 )); then
    has_audio=true
fi

# Name:height:target_bitrate:maxrate:bufsize
ladder=(
    "2160p:2160:12000k:12840k:18000k"
    "1440p:1440:7800k:8346k:11700k"
    "1080p:1080:4500k:4815k:6750k"
    "720p:720:2800k:2996k:4200k"
    "540p:540:1800k:1926k:2700k"
    "360p:360:1000k:1070k:1500k"
    "240p:240:600k:642k:900k"
)

declare -a variant_names=()
declare -a variant_heights=()
declare -a variant_bitrates=()
declare -a variant_maxrates=()
declare -a variant_bufsizes=()

for variant in "${ladder[@]}"; do
    IFS=':' read -r name height bitrate maxrate bufsize <<< "${variant}"
    if (( source_height >= height )); then
        variant_names+=("${name}")
        variant_heights+=("${height}")
        variant_bitrates+=("${bitrate}")
        variant_maxrates+=("${maxrate}")
        variant_bufsizes+=("${bufsize}")
    fi
done

variant_count="${#variant_names[@]}"
(( variant_count > 0 )) || die "No valid output variants were selected"

for name in "${variant_names[@]}"; do
    mkdir -p "${OUTPUT_DIR}/${name}"
done

split_targets=()
for idx in "${!variant_names[@]}"; do
    split_targets+=("[vsplit${idx}]")
done

split_joined="$(printf '%s' "${split_targets[@]}")"
filter_complex="[0:v]split=${variant_count}${split_joined};"
for idx in "${!variant_names[@]}"; do
    height="${variant_heights[$idx]}"
    filter_complex+="${split_targets[$idx]}scale=-2:${height}:flags=lanczos[v${idx}];"
done
filter_complex="${filter_complex%;}"

var_stream_map_parts=()
ffmpeg_args=(
    -hide_banner
    -y
    -i "${INPUT_FILE}"
    -filter_complex "${filter_complex}"
)

for idx in "${!variant_names[@]}"; do
    ffmpeg_args+=(
        -map "[v${idx}]"
        -c:v:${idx} libx264
        -preset:v:${idx} slow
        -profile:v:${idx} high
        -pix_fmt:v:${idx} yuv420p
        -sc_threshold:v:${idx} 0
        -g:v:${idx} 60
        -keyint_min:v:${idx} 60
        -b:v:${idx} "${variant_bitrates[$idx]}"
        -maxrate:v:${idx} "${variant_maxrates[$idx]}"
        -bufsize:v:${idx} "${variant_bufsizes[$idx]}"
    )

    if [[ "${has_audio}" == "true" ]]; then
        ffmpeg_args+=(
            -map 0:a:0?
            -c:a:${idx} aac
            -b:a:${idx} 128k
            -ac:a:${idx} 2
            -ar:a:${idx} 48000
        )
        var_stream_map_parts+=("v:${idx},a:${idx},name:${variant_names[$idx]}")
    else
        var_stream_map_parts+=("v:${idx},name:${variant_names[$idx]}")
    fi
done

var_stream_map="$(printf '%s ' "${var_stream_map_parts[@]}")"
var_stream_map="${var_stream_map% }"

echo "Input file: ${INPUT_FILE}"
echo "Output dir: ${OUTPUT_DIR}"
echo "Variants:   ${variant_names[*]}"
echo "Audio:      ${has_audio}"
echo ""
echo "Encoding HLS ladder..."

time ffmpeg "${ffmpeg_args[@]}" \
    -f hls \
    -hls_time "${SEGMENT_DURATION}" \
    -hls_playlist_type vod \
    -hls_list_size 0 \
    -hls_flags independent_segments \
    -hls_segment_type mpegts \
    -master_pl_name "master.m3u8" \
    -var_stream_map "${var_stream_map}" \
    -hls_segment_filename "${OUTPUT_DIR}/%v/segment_%05d.ts" \
    "${OUTPUT_DIR}/%v/index.m3u8"

echo ""
echo "HLS package complete."
echo "Master playlist: ${OUTPUT_DIR}/master.m3u8"
echo ""
echo "Example S3 sync commands:"
echo "  aws s3 sync \"${OUTPUT_DIR}/\" \"s3://YOUR_BUCKET/YOUR_PREFIX/\" --exclude \"*\" --include \"*.ts\" --cache-control \"public,max-age=31536000,immutable\" --content-type \"video/mp2t\""
echo "  aws s3 sync \"${OUTPUT_DIR}/\" \"s3://YOUR_BUCKET/YOUR_PREFIX/\" --exclude \"*\" --include \"*.m3u8\" --cache-control \"public,max-age=60\" --content-type \"application/vnd.apple.mpegurl\""
