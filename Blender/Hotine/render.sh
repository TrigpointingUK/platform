#!/usr/bin/env bash
# render.sh — Render the trig pillar flythrough and assemble the video.
#
# Usage:
#   ./render.sh              # Render all frames, then assemble MP4
#   ./render.sh --assemble   # Skip rendering, just assemble existing frames
#   ./render.sh --preview    # Render every 10th frame for a quick preview
#
# The script is resume-safe: already-rendered frames are skipped
# (Blender's use_overwrite is off).  If a render is interrupted,
# just re-run and it picks up where it left off.
#
# Requirements:
#   - blender (tested with 4.3)
#   - ffmpeg
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BLEND_SCRIPT="${SCRIPT_DIR}/trig_pillar.py"
FRAMES_DIR="${SCRIPT_DIR}/frames"
OUTPUT="${SCRIPT_DIR}/trig_flythrough.mp4"
FPS=30

# ── Locate Blender ─────────────────────────────────────────────
# Prefer the official Blender (which includes OIDN denoiser) over
# the Ubuntu-packaged version which lacks it.
OFFICIAL_BLENDER="${SCRIPT_DIR}/../blender-4.3.2-linux-x64/blender"
if [ -x "${OFFICIAL_BLENDER}" ]; then
    BLENDER="${OFFICIAL_BLENDER}"
    echo "  Using official Blender: ${BLENDER}"
else
    BLENDER="blender"
    echo "  Using system Blender (OIDN may not be available)"
fi

# ── Parse arguments ──────────────────────────────────────────────
ASSEMBLE_ONLY=false
PREVIEW=false
for arg in "$@"; do
    case "$arg" in
        --assemble) ASSEMBLE_ONLY=true ;;
        --preview)  PREVIEW=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── Render frames ────────────────────────────────────────────────
if [ "$ASSEMBLE_ONLY" = false ]; then
    mkdir -p "${FRAMES_DIR}"

    echo "============================================="
    echo "  Rendering frames"
    echo "  Output: ${FRAMES_DIR}/"
    echo "============================================="

    RENDER_ARGS=(
        "${BLENDER}" --background
        --python "${BLEND_SCRIPT}"
    )

    if [ "$PREVIEW" = true ]; then
        echo "  (Preview mode: every 10th frame)"
        RENDER_ARGS+=(--render-anim --frame-jump 10)
    else
        RENDER_ARGS+=(--render-anim)
    fi

    echo ""
    time "${RENDER_ARGS[@]}"
    echo ""
fi

# ── Count rendered frames ────────────────────────────────────────
FRAME_COUNT=$(find "${FRAMES_DIR}" -maxdepth 1 -name '*.png' | wc -l)
echo "  Rendered frames: ${FRAME_COUNT}"

if [ "$FRAME_COUNT" -eq 0 ]; then
    echo "ERROR: No frames found in ${FRAMES_DIR}/"
    exit 1
fi

# ── Assemble video with FFmpeg ───────────────────────────────────
echo ""
echo "============================================="
echo "  Assembling video"
echo "  Output: ${OUTPUT}"
echo "============================================="
echo ""

ffmpeg -y \
    -framerate "${FPS}" \
    -i "${FRAMES_DIR}/%04d.png" \
    -c:v libx264 \
    -preset slow \
    -crf 18 \
    -pix_fmt yuv420p \
    -movflags +faststart \
    "${OUTPUT}"

echo ""
echo "============================================="
echo "  Done!"
echo "  Video: ${OUTPUT}"
echo "  Size:  $(du -h "${OUTPUT}" | cut -f1)"
echo "============================================="

