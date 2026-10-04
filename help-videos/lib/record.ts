/**
 * Render one clip: load and settle the page off-camera, then capture the title
 * card and the clip's performance, encoding to H.264 MP4 plus a poster JPEG.
 */

import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";

import { catalogueEntry, sectionTitle } from "./catalogue.ts";
import { BASE_URL, type Clip } from "./clip.ts";
import { Director } from "./director.ts";
import type { Profile } from "./profiles.ts";
import { Screencast } from "./screencast.ts";

export interface Rendered {
  mp4: string;
  /** Where the clip finished - the page state a "try it" link should reproduce. */
  finalUrl: string;
}

export async function record(clip: Clip, profile: Profile, outRoot: string): Promise<Rendered> {
  const outDir = join(outRoot, profile.name);
  mkdirSync(outDir, { recursive: true });
  const framesDir = mkdtempSync(join(tmpdir(), `hv-${clip.id}-${profile.name}-`));

  const browser = await chromium.launch({ args: profile.launchArgs });
  const context = await browser.newContext({
    ...profile.context,
    locale: "en-GB",
    timezoneId: "Europe/London",
    colorScheme: "light",
    ...(clip.geolocation ? { geolocation: clip.geolocation, permissions: ["geolocation"] } : {}),
  });

  try {
    await Director.install(context, profile.mobile);
    const page = await context.newPage();
    const director = new Director(page, clip.id, profile.mobile);

    // Off camera: load, settle and cover the page with the title card.
    await page.goto(new URL(clip.path, BASE_URL).toString());
    await director.settle();
    await clip.setup?.(page);
    const viewport = page.viewportSize()!;
    await director.placeCursor(viewport.width * 0.62, viewport.height * 0.55);
    const entry = catalogueEntry(clip.id);
    await director.showTitle(sectionTitle(entry), entry.question);

    const screencast = new Screencast(page, framesDir, profile.videoSize);
    await screencast.start();
    await director.dismissTitle();
    await clip.run(director);
    await director.pause(1200);
    await screencast.stop();
    const finalUrl = page.url();

    const mp4 = join(outDir, `${clip.id}.mp4`);
    const poster = join(outDir, `${clip.id}.jpg`);
    screencast.encode(mp4);
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-sseof", "-1", "-i", mp4, "-frames:v", "1", "-q:v", "3", poster]);
    return { mp4, finalUrl };
  } finally {
    await browser.close();
    rmSync(framesDir, { recursive: true, force: true });
  }
}
