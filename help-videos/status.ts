/** List the help catalogue by section, showing which entries have clip scripts. */

import { catalogueErrors, HELP_CATALOGUE, HELP_SECTIONS, loadClips } from "./lib/catalogue.ts";

const scripted = new Set((await loadClips()).map((c) => c.id));
const width = Math.max(...HELP_CATALOGUE.map((e) => e.id.length));

for (const section of HELP_SECTIONS) {
  const entries = HELP_CATALOGUE.filter((e) => e.section === section.id);
  console.log(`\n${section.title}`);
  if (entries.length === 0) console.log("  (nothing yet)");
  for (const e of entries) {
    const mark = scripted.has(e.id) ? "✓" : "·";
    const gaps = [!e.answer && "no answer", !e.tryIt && "no try-it link"].filter(Boolean).join(", ");
    console.log(`  ${mark} ${e.id.padEnd(width)}  ${e.question}${gaps ? `  [${gaps}]` : ""}`);
  }
}

const ideas = HELP_CATALOGUE.length - scripted.size;
console.log(`\n${scripted.size} scripted, ${ideas} ${ideas === 1 ? "idea" : "ideas"}  (✓ scripted, · idea)`);

const errors = catalogueErrors();
if (errors.length) {
  console.error(`\nCatalogue errors:\n  ${errors.join("\n  ")}`);
  process.exit(1);
}
