/** Joins the help catalogue (shared with the web app) to the clip scripts. */

import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { HELP_CATALOGUE, HELP_SECTIONS, type HelpEntry } from "../../web/src/help/catalogue.ts";
import type { Clip } from "./clip.ts";

export { HELP_CATALOGUE, HELP_SECTIONS, type HelpEntry };

const clipsDir = join(dirname(fileURLToPath(import.meta.url)), "..", "clips");

export function sectionTitle(entry: HelpEntry): string {
  return HELP_SECTIONS.find((s) => s.id === entry.section)?.title ?? entry.section;
}

export function catalogueEntry(id: string): HelpEntry {
  const entry = HELP_CATALOGUE.find((e) => e.id === id);
  if (!entry) throw new Error(`Clip "${id}" has no entry in web/src/help/catalogue.ts`);
  return entry;
}

/** Every clip script, checked against the catalogue. */
export async function loadClips(): Promise<Clip[]> {
  const clips: Clip[] = [];
  for (const f of readdirSync(clipsDir).filter((f) => f.endsWith(".ts")).sort()) {
    const { clip } = (await import(pathToFileURL(join(clipsDir, f)).href)) as { clip: Clip };
    if (`${clip.id}.ts` !== f) throw new Error(`clips/${f} exports id "${clip.id}"; rename one to match`);
    catalogueEntry(clip.id);
    clips.push(clip);
  }
  return clips;
}

/** Catalogue problems that would break the help page or the renders. */
export function catalogueErrors(): string[] {
  const errors: string[] = [];
  const seen = new Set<string>();
  for (const e of HELP_CATALOGUE) {
    if (seen.has(e.id)) errors.push(`duplicate id "${e.id}"`);
    seen.add(e.id);
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(e.id)) errors.push(`id "${e.id}" isn't kebab-case`);
  }
  return errors;
}
