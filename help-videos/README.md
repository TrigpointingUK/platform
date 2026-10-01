# Help videos

Scripted, reproducible screen recordings of the trigs-v2 page for the FAQ and
tip-of-the-day. Each clip is a Playwright script that drives production the way
a person would, with captions and highlights, rendered to H.264 MP4 plus a
poster JPEG. Every clip is rendered for two profiles from the same script:

- `desktop` - 1280×800, visible cursor with curved mouse paths and click ripples.
- `mobile` - iPhone 13 layout (390×664 CSS px, touch), captured at 2× (780×1328);
  taps show a fingertip dot and scrolling is a visible swipe.

```bash
make help-videos-install                  # once: npm ci + Chromium
make help-videos                          # every clip, both profiles → out/<profile>/
make help-videos ONLY=nearest-trig        # one clip (space-separate for several)
make help-videos PROFILE=mobile           # one profile
```

Frames come from the Chrome DevTools screencast (see
[lib/screencast.ts](lib/screencast.ts)), not Playwright's `recordVideo`, which
records CSS-pixel VP8. The mobile profile forces `--force-device-scale-factor=2`
because the screencast is otherwise CSS-pixel sized too.

Set `HELP_VIDEO_BASE_URL` to record against staging or a local dev server
(default `https://trigpointing.uk`). Recording only reads data.

## Writing a clip

Add `clips/<section>/<id>.ts` exporting a `Clip` (see [lib/clip.ts](lib/clip.ts)).
The recorder loads the page, shows the section and question as a title card,
then calls `run(director)`. Use the `Director` ([lib/director.ts](lib/director.ts))
for everything on camera: `click`, `hover`, `type`, `caption`, `highlight`,
`settle` (waits for API calls and map tiles). The same calls tap and swipe on
mobile; branch on `d.mobile` only where the page genuinely differs - e.g.
`collapseFilters(d)` to fold the trigs-v2 filter panel away so the results fit
on a phone screen. Shared trigs-v2 locators and helpers live in
[lib/trigsV2.ts](lib/trigsV2.ts); prefer role/label locators over CSS classes.

Mouse paths are seeded from the clip id, so re-renders move identically; only
live data (counts, names) changes. A clip that fails to render usually means the
UI changed and the video is stale.
