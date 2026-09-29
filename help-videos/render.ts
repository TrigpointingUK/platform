/**
 * Render help video clips.
 *
 *   npm run render                 # every clip
 *   npm run render -- nearest-trig # only the named clip(s)
 */

import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import type { Clip } from "./lib/clip.ts";
import { record } from "./lib/record.ts";

const root = dirname(fileURLToPath(import.meta.url));
const outDir = join(root, "out");

async function loadClips(): Promise<Clip[]> {
  const files = readdirSync(join(root, "clips"), { recursive: true, encoding: "utf8" })
    .filter((f) => f.endsWith(".ts"))
    .sort();
  const clips: Clip[] = [];
  for (const f of files) {
    const mod = (await import(pathToFileURL(join(root, "clips", f)).href)) as { clip: Clip };
    clips.push(mod.clip);
  }
  return clips;
}

const only = process.argv.slice(2);
const clips = (await loadClips()).filter((c) => only.length === 0 || only.includes(c.id));
if (clips.length === 0) {
  console.error(`No clips matched: ${only.join(", ")}`);
  process.exit(1);
}

let failed = 0;
for (const clip of clips) {
  const started = Date.now();
  try {
    const mp4 = await record(clip, outDir);
    console.log(`✓ ${clip.id} → ${mp4} (${((Date.now() - started) / 1000).toFixed(1)}s)`);
  } catch (err) {
    failed++;
    console.error(`✗ ${clip.id}: ${(err as Error).message}`);
  }
}
process.exit(failed ? 1 : 0);
