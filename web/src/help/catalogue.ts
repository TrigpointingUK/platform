/**
 * Help catalogue - every question the help pages answer, in display order.
 *
 * The single source of truth for the FAQ, tip-of-the-day and the scripted
 * help videos in help-videos/. An entry is an "idea" until a clip script
 * exists at help-videos/clips/<id>.ts; `make help-videos-status` lists both.
 *
 * To add an idea: append an entry with an id, section and question. Notes are
 * for us (what the clip should show, caveats) and are never displayed.
 */

export const HELP_SECTIONS = [
  { id: "first-trigpoint", title: "Finding your first trigpoint" },
  { id: "planning", title: "Planning a trip" },
  { id: "data-mining", title: "Data mining UK trigpoints" },
] as const;

export type HelpSectionId = (typeof HELP_SECTIONS)[number]["id"];

export interface HelpEntry {
  /** Kebab-case; also the clip script and video filename. Never change once published. */
  id: string;
  section: HelpSectionId;
  question: string;
  /** Markdown answer shown with the video. */
  answer?: string;
  /** Site path that reproduces the clip's end state, for a "Try it" link. */
  tryIt?: string;
  /** For us only: what the clip should show, open questions. */
  notes?: string;
}

export const HELP_CATALOGUE: HelpEntry[] = [
  {
    id: "nearest-trig",
    section: "first-trigpoint",
    question: "How do I find the nearest trigpoint?",
    answer:
      "Open the trigpoints page and allow your location when asked: the list is centred on you, " +
      "nearest first. The very nearest is often a church spire or mast you can't visit, so open " +
      "**Type** and choose **Pillar** (or whichever types you're after). Tap a trigpoint for " +
      "directions, photos and logs.\n\n" +
      "On a phone, tap any empty space in the filter panel to fold it away and see the list; " +
      "tap the results bar to bring it back.",
    tryIt: "/experiment/trigs-v2?types=PILLAR,HOTINE,VANESSA,STONE_PILLAR",
  },
  {
    id: "log-a-trigpoint",
    section: "first-trigpoint",
    question: "I'm standing at a trigpoint - how do I log it?",
    notes:
      "Needs a logged-in user: decide how the recorder signs in (password login or a demo " +
      "account). Flow: trigs-v2 with " +
      "geolocation at the trig, it's top of the list at 0.0 km, open it, Log, fill in condition " +
      "and comment, add a photo? Must not submit a real log on production - stop before Save, or " +
      "record against staging.",
  },
  {
    id: "damaged-pillars-west-yorkshire",
    section: "data-mining",
    question: "How many damaged pillars are there in West Yorkshire?",
    answer:
      "Set three filters and read the count above the list: **Type** → Pillar, **Condition** → " +
      "Damaged, and **Area** → choose *Ceremonial County*, then West Yorkshire. Sorting the area " +
      "list by **Nearest** puts the areas around you at the top.",
    tryIt: "/experiment/trigs-v2?types=PILLAR,HOTINE,VANESSA,STONE_PILLAR&conditions=D&areas=965",
  },
];
