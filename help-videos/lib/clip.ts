import type { Page } from "playwright";
import type { Director } from "./director.ts";

export const BASE_URL = process.env.HELP_VIDEO_BASE_URL ?? "https://trigpointing.uk";

/** Leeds city centre - a recognisable, trig-dense spot for "near me" clips. */
export const LEEDS = { latitude: 53.7997, longitude: -1.5492 };

/** The on-camera script for one catalogue entry (web/src/help/catalogue.ts). */
export interface Clip {
  /** Catalogue id; also the output filename. The title card comes from the catalogue. */
  id: string;
  /** Path (relative to BASE_URL) the clip starts on. */
  path: string;
  geolocation?: { latitude: number; longitude: number };
  /** Off-camera preparation after the page loads (dismiss banners etc.). */
  setup?: (page: Page) => Promise<void>;
  /** The on-camera performance. */
  run: (d: Director) => Promise<void>;
}
