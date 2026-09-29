/**
 * Render one clip: load and settle the page off-camera, perform the clip,
 * then trim the lead-in and encode to H.264 MP4 plus a poster JPEG.
 */

import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";

import { BASE_URL, type Clip } from "./clip.ts";
import { Director } from "./director.ts";

const VIEWPORT = { width: 1280, height: 800 };

export async function record(clip: Clip, outDir: string): Promise<string> {
  mkdirSync(outDir, { recursive: true });
  const rawDir = mkdtempSync(join(tmpdir(), `hv-${clip.id}-`));

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: rawDir, size: VIEWPORT },
    locale: "en-GB",
    timezoneId: "Europe/London",
    colorScheme: "light",
    ...(clip.geolocation ? { geolocation: clip.geolocation, permissions: ["geolocation"] } : {}),
  });

  try {
    await Director.install(context);
    const page = await context.newPage();
    const recordingStarted = performance.now();

    const director = new Director(page, clip.id);
    await page.goto(new URL(clip.path, BASE_URL).toString());
    await director.settle();
    await clip.setup?.(page);
    await director.placeCursor(VIEWPORT.width * 0.62, VIEWPORT.height * 0.55);
    await director.showTitle(clip.section, clip.question);
    await director.pause(600);

    // Playwright's video starts a little after the page is created, so the
    // wall-clock lead-in overshoots. Cutting early only shortens the static
    // title card, never the performance.
    const leadIn = Math.max(0, (performance.now() - recordingStarted) / 1000 - 0.5);
    await director.dismissTitle();
    await clip.run(director);
    await director.pause(1200);

    const video = page.video();
    await context.close();
    const rawPath = await video!.path();

    const mp4 = join(outDir, `${clip.id}.mp4`);
    const poster = join(outDir, `${clip.id}.jpg`);
    execFileSync("ffmpeg", [
      "-y", "-loglevel", "error",
      "-ss", leadIn.toFixed(2), "-i", rawPath,
      "-c:v", "libx264", "-preset", "slow", "-crf", "20",
      "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
      mp4,
    ]);
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-sseof", "-1", "-i", mp4, "-frames:v", "1", "-q:v", "3", poster]);
    return mp4;
  } finally {
    await browser.close();
    rmSync(rawDir, { recursive: true, force: true });
  }
}
