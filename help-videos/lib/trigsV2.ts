/** Locators for the trigs-v2 page, shared between clips. */

import type { Page } from "playwright";

import type { Director } from "./director.ts";

export const TRIGS_V2 = "/experiment/trigs-v2";

export const chip = (page: Page, label: string) =>
  page.getByRole("button", { name: new RegExp(`^${label}:`) });

export const popover = (page: Page, label: string) =>
  page.getByRole("dialog", { name: `${label} filter options` });

/** The visible label text of a checkbox row inside a popover (the input itself is sr-only). */
export const option = (page: Page, chipLabel: string, text: string) =>
  popover(page, chipLabel).getByText(text, { exact: true });

/** Chevron that expands a Type category to show its sub-types. */
export const expandCategory = (page: Page, category: string) =>
  option(page, "Type", category).locator("xpath=ancestor::div[1]/button");

export const resultCards = (page: Page) =>
  page.getByRole("main").getByRole("link").filter({ has: page.getByRole("heading", { level: 3 }) });

export const resultCount = (page: Page) =>
  page.getByRole("main").locator("strong").filter({ hasText: /^[\d,]+$/ }).first();

/**
 * Fold the filter panel away by tapping empty space beside the "Sort"
 * heading - any background tap in the panel toggles it (see TrigsV2.tsx).
 */
export async function collapseFilters(d: Director): Promise<void> {
  await d.clickBeside(d.page.getByRole("main").getByText("Sort", { exact: true }), 90);
  await d.settle();
}

/** Bring the filters back by tapping empty space in the results summary row. */
export async function expandFilters(d: Director): Promise<void> {
  await d.clickBeside(resultCount(d.page).locator("xpath=.."), 16);
  await d.settle();
}
