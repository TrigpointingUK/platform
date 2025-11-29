### UK map calibration JSON

This file documents the structure and semantics of `res/uk_map_calibration.json`, which calibrates WGS84 coordinates to pixel positions for the UK map image.

### File location

- `res/uk_map_calibration.json` — JSON payload produced by `scripts/calibrate_map.py`
- `res/ukmap.jpg` — the base image the calibration was fitted against

### Fields

- **affine**: 2×3 matrix A that maps WGS84 lon/lat to image pixels.
  - Structure: `[[a, b, tx], [c, d, ty]]`
  - Forward mapping:
    - `x = a*lon + b*lat + tx`
    - `y = c*lon + d*lat + ty`
  - Notes:
    - Inputs are longitude/latitude in degrees; outputs are pixels.
    - Image origin is top‑left; `y` increases downwards.
    - `a,d` control scale per degree; `b,c` encode rotation/shear; `tx,ty` are translations.

- **inverse**: 2×3 matrix `A_inv`, the algebraic inverse of `affine`.
  - Structure: `[[p, q, u], [r, s, v]]`
  - Reverse mapping:
    - `lon = p*x + q*y + u`
    - `lat = r*x + s*y + v`
  - Regenerate this if you edit `affine` (treat both as 3×3 with a final `[0,0,1]` row when inverting).

- **pixel_bbox**: `[left, top, right, bottom]` rectangle (pixels) used for fitting/rendering.
  - Use a tight box around the drawn coastline (exclude margins/drop shadows) for best accuracy.
  - Coordinates are in the final image pixel space.

- **bounds_geo**: `[lon_west, lat_south, lon_east, lat_north]`
  - Geographic extent that corresponds to `pixel_bbox`, derived from `inverse`.
  - Useful for sanity checks and coarse clipping.

### Recomputing `inverse` after editing `affine`

```python
import json, numpy as np

path = "res/uk_map_calibration.json"
d = json.load(open(path))
A = np.array(d["affine"], dtype=float)
M = np.vstack([A, [0, 0, 1]])
Minv = np.linalg.inv(M)[:2]
d["inverse"] = Minv.tolist()
json.dump(d, open(path, "w"), indent=2)
```

### Tweaking tips

- **Shift** the map: adjust `tx, ty` in `affine`.
- **Uniform scale**: multiply the lon column `[a, c]` and/or the lat column `[b, d]`.
- **Rotate/shear**: adjust the cross terms `b, c`.
- Always regenerate `inverse` after modifying `affine`.

### Programmatic use

- Forward (lon,lat → x,y): apply `affine`.
- Reverse (x,y → lon,lat): apply `inverse`.
- In code, use `CalibrationResult.lonlat_to_xy` and `CalibrationResult.xy_to_lonlat` from `app.utils.geocalibrate`.

### API exposure for frontend mini maps

- `/v1/logs` responses now include `trig_lat` and `trig_lon` fields (in the
  `TLogResponse` schema) so the SPA can plot log locations without an extra API
  call.
- The SPA loads `stretched53_default.(png|json)` directly from
  `web/public/maps/mini-map/` and reuses the same affine matrices documented
  above.
- When regenerating map assets, update both the backend `res/` copies _and_ the
  frontend public copies to keep the calibration data in sync.
