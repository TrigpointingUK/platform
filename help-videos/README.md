# Help videos

Scripted, reproducible screen recordings of the trigs-v2 page for the FAQ and
tip-of-the-day. Each clip is a Playwright script that drives production the way
a person would (visible cursor, curved mouse paths, human typing) with captions
and highlights, rendered to H.264 MP4 plus a poster JPEG.

```bash
make help-videos-install                  # once: npm ci + Chromium
make help-videos                          # render every clip to out/
make help-videos ONLY=nearest-trig        # render one (space-separate for several)
```

Set `HELP_VIDEO_BASE_URL` to record against staging or a local dev server
(default `https://trigpointing.uk`). Recording only reads data.

## Writing a clip

Add `clips/<section>/<id>.ts` exporting a `Clip` (see [lib/clip.ts](lib/clip.ts)).
The recorder loads the page, shows the section and question as a title card,
then calls `run(director)`. Use the `Director` ([lib/director.ts](lib/director.ts))
for everything on camera: `click`, `hover`, `type`, `caption`, `highlight`,
`settle` (waits for API calls and map tiles). Shared trigs-v2 locators live in
[lib/trigsV2.ts](lib/trigsV2.ts); prefer role/label locators over CSS classes.

Mouse paths are seeded from the clip id, so re-renders move identically; only
live data (counts, names) changes. A clip that fails to render usually means the
UI changed and the video is stale.
