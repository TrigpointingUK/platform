# Map Styling Guide

This guide explains how to create pre-styled map variants for the `/v1/trigs/{trigid}/map` endpoint.

## Overview

The `/v1/trigs/{trigid}/map` endpoint now uses pre-styled map images for performance. Instead of recolouring and scaling images on every request, you create styled variants ahead of time using the `make_styled_map.py` script.

## Workflow

1. **Experiment** with styling parameters using the script
2. **Generate** styled [.png, .json] pairs
3. **Copy** files to `res/` directory
4. **Use** in API via the `style` parameter

### Shipping to the SPA mini map

- Copy the same `.png` and `.json` files to `web/public/maps/mini-map/` so the
  `/logs` page can render its embedded map without calling `/v1/trigs/{id}/map`.
- Keep the filenames in sync between `res/` and `web/public` to avoid confusing
  diffs and ensure both layers use the same calibration matrices.

## Script Usage

### Basic Syntax

```bash
python scripts/make_styled_map.py \
  --input-png <source.png> \
  --input-json <source.json> \
  --output-png <output.png> \
  --output-json <output.json> \
  --land-colour <hex> \
  --coastline-colour <hex> \
  --height <pixels>
```

### Example: Create Default Styled Map

This recreates the original API endpoint defaults (grey land, dark grey coastline, 110px height):

```bash
python scripts/make_styled_map.py \
  --input-png res/ukmap_wgs84_stretched53.png \
  --input-json res/uk_map_calibration_wgs84_stretched53.json \
  --output-png res/stretched53_default.png \
  --output-json res/stretched53_default.json \
  --land-colour '#dddddd' \
  --coastline-colour '#666666' \
  --height 110
```

### Example: Create High-Contrast Variant

```bash
python scripts/make_styled_map.py \
  --input-png res/ukmap_wgs84_stretched53.png \
  --input-json res/uk_map_calibration_wgs84_stretched53.json \
  --output-png res/stretched53_highcontrast.png \
  --output-json res/stretched53_highcontrast.json \
  --land-colour '#ffffff' \
  --coastline-colour '#000000' \
  --height 110
```

### Example: Create Larger Map

```bash
python scripts/make_styled_map.py \
  --input-png res/ukmap_wgs84_stretched53.png \
  --input-json res/uk_map_calibration_wgs84_stretched53.json \
  --output-png res/stretched53_large.png \
  --output-json res/stretched53_large.json \
  --land-colour '#e8e8e8' \
  --coastline-colour '#555555' \
  --height 400
```

### Example: Use WGS84 (Non-Stretched) Base

```bash
python scripts/make_styled_map.py \
  --input-png res/ukmap_wgs84.png \
  --input-json res/uk_map_calibration_wgs84.json \
  --output-png res/wgs84_default.png \
  --output-json res/wgs84_default.json \
  --land-colour '#dddddd' \
  --coastline-colour '#666666' \
  --height 110
```

### Example: No Recolouring (Keep Original)

```bash
python scripts/make_styled_map.py \
  --input-png res/ukmap_wgs84_stretched53.png \
  --input-json res/uk_map_calibration_wgs84_stretched53.json \
  --output-png res/stretched53_original.png \
  --output-json res/stretched53_original.json \
  --height 110
```

(Omitting `--land-colour` preserves the original image colours)

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--input-png` | Yes | - | Source PNG file path |
| `--input-json` | Yes | - | Source calibration JSON file |
| `--output-png` | Yes | - | Output PNG file path |
| `--output-json` | Yes | - | Output calibration JSON file |
| `--land-colour` | No | None | Hex colour for land (e.g. `#dddddd`). Omit to keep original. |
| `--coastline-colour` | No | None | Hex colour for coastline stroke (e.g. `#666666`) |
| `--height` | No | None | Target height in pixels. Width scales proportionally. |

## API Usage

Once you've created styled variants, use them in the API:

```http
GET /v1/trigs/{trigid}/map?style=stretched53_default&dot_colour=#ff0000&dot_diameter=50
```

### API Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `style` | `stretched53_default` | Base filename (without extension) of [.png, .json] pair in `res/` |
| `dot_colour` | `#0000ff` | Hex colour for the trig point dot |
| `dot_diameter` | `50` | Dot diameter in pixels (1-100) |

## Available Base Maps

- `ukmap_wgs84_stretched53.png` + `.json` - Latitude-stretched projection (cos 53°)
- `ukmap_wgs84.png` + `.json` - Pure WGS84 equirectangular projection

## Migration from Old Endpoint

The previous endpoint accepted these parameters (now deprecated):

- `map_variant` → replaced by pre-styled `style` parameter
- `land_colour` → apply during styling, not runtime
- `coastline_colour` → apply during styling, not runtime
- `height` → apply during styling, not runtime
- `dot_colour` → **kept** (cheap to draw at runtime)
- `dot_diameter` → **kept** (cheap to draw at runtime)

### Old Endpoint Call (Slow)

```http
GET /v1/trigs/123/map?map_variant=stretched53&land_colour=#dddddd&coastline_colour=#666666&height=110&dot_colour=#0000ff&dot_diameter=50
```

### New Endpoint Call (Fast)

```http
GET /v1/trigs/123/map?style=stretched53_default&dot_colour=#0000ff&dot_diameter=50
```

(Pre-generate `stretched53_default.png` using the script with the land/coastline/height parameters)

## Technical Details

### Affine Transformation Scaling

The script automatically scales the affine transformation matrices in the calibration JSON when you change the image size. This ensures coordinate transformations remain accurate.

### Alpha Channel Preservation

The script preserves the alpha channel (transparency) from the source image, ensuring clean composition with background layers.

### Edge Detection

Coastline stroke is generated using Pillow's `FIND_EDGES` filter on the alpha channel, then dilated with `MaxFilter(3)` for a more visible stroke.
