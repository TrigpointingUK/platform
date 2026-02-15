#!/usr/bin/env bash
# render.sh — Render the trig pillar flythrough and assemble the video.
#
# Usage:
#   ./render.sh              # Render all frames, then assemble MP4
#   ./render.sh --assemble   # Skip rendering, just assemble existing frames
#   ./render.sh --draft      # Fast Cycles preview (low samples, half-res,
#                            #   every 5th frame) — good for checking flow
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
DRAFT=false
for arg in "$@"; do
    case "$arg" in
        --assemble) ASSEMBLE_ONLY=true ;;
        --preview)  PREVIEW=true ;;
        --draft)    DRAFT=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── Determine output paths and frame jump ────────────────────────
if [ "$DRAFT" = true ]; then
    FRAMES_DIR="${SCRIPT_DIR}/draft"
    OUTPUT="${SCRIPT_DIR}/trig_draft.mp4"
    FRAME_JUMP=5
    RENDER_QUALITY="draft"
    echo "  Mode: DRAFT (${FRAME_JUMP}× frame skip, low samples, half-res)"
elif [ "$PREVIEW" = true ]; then
    FRAMES_DIR="${SCRIPT_DIR}/frames"
    OUTPUT="${SCRIPT_DIR}/trig_flythrough.mp4"
    FRAME_JUMP=10
    RENDER_QUALITY="final"
    echo "  Mode: PREVIEW (${FRAME_JUMP}× frame skip, full quality)"
else
    FRAMES_DIR="${SCRIPT_DIR}/frames"
    OUTPUT="${SCRIPT_DIR}/trig_flythrough.mp4"
    FRAME_JUMP=1
    RENDER_QUALITY="final"
    echo "  Mode: FULL RENDER"
fi

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
        --render-anim
    )

    if [ "$FRAME_JUMP" -gt 1 ]; then
        RENDER_ARGS+=(--frame-jump "${FRAME_JUMP}")
    fi

    # Tell the Python script which quality level to configure
    export TRIG_RENDER_QUALITY="${RENDER_QUALITY}"

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

if [ "$FRAME_JUMP" -gt 1 ]; then
    # Sparse frames (every Nth).  Feed at 1/N of the real FPS so each
    # rendered frame is held for the correct duration, giving a jerky
    # but correctly-timed preview.
    INPUT_FPS=$((FPS / FRAME_JUMP))
    echo "  Sparse frames: input at ${INPUT_FPS} fps, output at ${FPS} fps"
    ffmpeg -y \
        -framerate "${INPUT_FPS}" \
        -pattern_type glob -i "${FRAMES_DIR}/*.png" \
        -c:v libx264 \
        -r "${FPS}" \
        -preset slow \
        -crf 18 \
        -pix_fmt yuv420p \
        -movflags +faststart \
        "${OUTPUT}"
else
    # Consecutive frames — use the standard sequential pattern
    ffmpeg -y \
        -framerate "${FPS}" \
        -i "${FRAMES_DIR}/%04d.png" \
        -c:v libx264 \
        -preset slow \
        -crf 18 \
        -pix_fmt yuv420p \
        -movflags +faststart \
        "${OUTPUT}"
fi

echo ""
echo "============================================="
echo "  Done!"
echo "  Video: ${OUTPUT}"
echo "  Size:  $(du -h "${OUTPUT}" | cut -f1)"
echo "============================================="
