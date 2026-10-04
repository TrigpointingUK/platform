/** Device profiles each clip is rendered for. */

import { devices, type BrowserContextOptions } from "playwright";

export type ProfileName = "desktop" | "mobile";

export interface Profile {
  name: ProfileName;
  mobile: boolean;
  context: BrowserContextOptions;
  /** Chromium flags; the screencast is CSS-pixel sized unless the device scale is forced. */
  launchArgs: string[];
  /** Maximum captured frame size (device pixels, downscaled to fit). */
  videoSize: { width: number; height: number };
}

// iPhone 13 viewport, touch and user agent; we always record with Chromium.
const { defaultBrowserType: _browser, ...iphone } = devices["iPhone 13"];

export const PROFILES: Record<ProfileName, Profile> = {
  desktop: {
    name: "desktop",
    mobile: false,
    context: { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 },
    launchArgs: [],
    videoSize: { width: 1280, height: 800 },
  },
  mobile: {
    name: "mobile",
    mobile: true,
    context: iphone,
    launchArgs: ["--force-device-scale-factor=2"],
    videoSize: { width: 780, height: 1328 },
  },
};
