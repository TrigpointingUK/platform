Mini trig map assets
====================

The `stretched53_default.(png|json)` pair in this folder is copied from
`/home/ianh/dev/platform/res/` and ships with the SPA so the `/logs` mini map
can be rendered entirely on the client.

To regenerate the assets:

1. Activate the virtual environment (`source venv/bin/activate`).
2. Run `python scripts/make_styled_map.py` with the desired styling parameters,
   pointing `--output-*` at the files inside this directory.
3. Keep the PNG and JSON filenames in sync so the frontend loader can find the
   calibration metadata.

These files live under `web/public`, so Vite serves them verbatim at
`/maps/mini-map/…` in both dev and production builds.

