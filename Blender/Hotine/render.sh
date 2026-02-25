#!/usr/bin/env bash
# render.sh — Render the trig pillar flythrough and assemble the video.
#
# Usage:
#   ./render.sh              # Render all frames, then assemble MP4
#   ./render.sh --assemble   # Skip rendering, just assemble existing frames
#   ./render.sh --draft      # Fast Cycles preview (low samples, half-res,
#                            #   every 5th frame) — good for checking flow
#   ./render.sh --preview    # Render every 10th frame for a quick preview
#   ./render.sh --bracket    # Flush bracket turntable orbit → transparent
#                            #   APNG (24 fps, 5 s, 2× oversampled PNGs)
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
BRACKET=false
for arg in "$@"; do
    case "$arg" in
        --assemble) ASSEMBLE_ONLY=true ;;
        --preview)  PREVIEW=true ;;
        --draft)    DRAFT=true ;;
        --bracket)  BRACKET=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── Determine output paths, frame rate, and frame jump ───────────
ANIMATION_MODE="flythrough"

if [ "$BRACKET" = true ]; then
    FPS=24
    FRAMES_DIR="${SCRIPT_DIR}/bracket"
    OUTPUT="${SCRIPT_DIR}/bracket_orbit.apng"
    FRAME_JUMP=1
    RENDER_QUALITY="final"
    ANIMATION_MODE="bracket"
    echo "  Mode: BRACKET ORBIT (${FPS} fps, transparent RGBA → APNG)"
elif [ "$DRAFT" = true ]; then
    FPS=30
    FRAMES_DIR="${SCRIPT_DIR}/draft"
    OUTPUT="${SCRIPT_DIR}/trig_draft.mp4"
    FRAME_JUMP=5
    RENDER_QUALITY="draft"
    echo "  Mode: DRAFT (${FRAME_JUMP}× frame skip, low samples, half-res)"
elif [ "$PREVIEW" = true ]; then
    FPS=30
    FRAMES_DIR="${SCRIPT_DIR}/preview"
    OUTPUT="${SCRIPT_DIR}/trig_preview.mp4"
    FRAME_JUMP=10
    RENDER_QUALITY="final"
    echo "  Mode: PREVIEW (${FRAME_JUMP}× frame skip, full quality)"
else
    FPS=30
    FRAMES_DIR="${SCRIPT_DIR}/frames"
    OUTPUT="${SCRIPT_DIR}/trig_flythrough.mp4"
    FRAME_JUMP=1
    RENDER_QUALITY="final"
    echo "  Mode: FULL RENDER"
fi

# ── Render frames ────────────────────────────────────────────────
if [ "$ASSEMBLE_ONLY" = false ]; then
    # For draft/preview renders, wipe old frames to prevent stale files
    # from a different render configuration contaminating the video.
    # Full renders are resume-safe (Blender skips existing frames).
    if [ "$FRAME_JUMP" -gt 1 ] && [ -d "${FRAMES_DIR}" ]; then
        STALE=$(find "${FRAMES_DIR}" -maxdepth 1 -name '*.png' | wc -l)
        if [ "$STALE" -gt 0 ]; then
            echo "  Clearing ${STALE} stale frames from ${FRAMES_DIR}/"
            rm -f "${FRAMES_DIR}"/*.png
        fi
    fi

    mkdir -p "${FRAMES_DIR}"

    echo "============================================="
    echo "  Rendering frames"
    echo "  Output: ${FRAMES_DIR}/"
    echo "============================================="

    RENDER_ARGS=(
        "${BLENDER}" --background
        --python "${BLEND_SCRIPT}"
    )

    # --frame-jump MUST come before --render-anim because Blender
    # processes arguments left-to-right and --render-anim triggers
    # the render immediately — anything after it is ignored.
    if [ "$FRAME_JUMP" -gt 1 ]; then
        RENDER_ARGS+=(--frame-jump "${FRAME_JUMP}")
    fi

    RENDER_ARGS+=(--render-anim)

    # Tell the Python script which quality level and animation to configure
    export TRIG_RENDER_QUALITY="${RENDER_QUALITY}"
    export TRIG_ANIMATION="${ANIMATION_MODE}"

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

# ── Assemble output ──────────────────────────────────────────────
echo ""
echo "============================================="

if [ "$BRACKET" = true ]; then
    # Assemble APNG — downsample 2× with Lanczos and set infinite loop.
    echo "  Assembling APNG"
    echo "  Output: ${OUTPUT}"
    echo "============================================="
    echo ""

    ffmpeg -y \
        -framerate "${FPS}" \
        -i "${FRAMES_DIR}/%04d.png" \
        -vf "scale=iw/2:ih/2:flags=lanczos" \
        -plays 0 \
        -f apng \
        "${OUTPUT}"
else
    # Assemble MP4 video
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
fi

echo ""
echo "============================================="
echo "  Done!"
echo "  Output: ${OUTPUT}"
echo "  Size:   $(du -h "${OUTPUT}" | cut -f1)"
echo "============================================="
