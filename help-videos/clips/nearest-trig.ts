import { LEEDS, type Clip } from "../lib/clip.ts";
import { chip, collapseFilters, expandFilters, option, resultCards, TRIGS_V2 } from "../lib/trigsV2.ts";

export const clip: Clip = {
  id: "nearest-trig",
  path: TRIGS_V2,
  geolocation: LEEDS,
  async run(d) {
    const page = d.page;
    await d.caption("The list starts from where you are, nearest first", 400);
    await d.hover(chip(page, "Centre on"), 200);
    await d.highlight(chip(page, "Centre on"), 1400);
    await d.hover(page.getByRole("button", { name: "Distance" }), 200);
    await d.highlight(page.getByRole("button", { name: "Distance" }), 1400);

    if (d.mobile) {
      await d.caption("Tap any empty space to fold the filters away", 300);
      await collapseFilters(d);
    }

    const first = resultCards(page).first();
    await d.hover(first, 200);
    await d.caption("The very nearest may be a church spire you can't visit…", 2000);

    if (d.mobile) {
      await d.caption("Tap the results bar to bring the filters back…", 300);
      await expandFilters(d);
    }
    await d.caption(d.mobile ? "…and use Type to show only pillars" : "…so use Type to show only pillars", 300);
    await d.click(chip(page, "Type"));
    await d.click(page.getByRole("dialog").getByRole("button", { name: "None", exact: true }));
    await d.click(option(page, "Type", "Pillar"));
    await d.click(chip(page, "Type"));
    await d.settle();
    if (d.mobile) await collapseFilters(d);

    const name = await resultCards(page).first().getByRole("heading").innerText();
    await d.hover(resultCards(page).first(), 200);
    await d.caption(`Your nearest pillar is ${name}`, 300);
    await d.highlight(resultCards(page).first(), 2200);

    await d.caption("Click it for directions, photos and logs", 300);
    await d.click(resultCards(page).first(), 200);
    await d.settle();
    await d.pause(2400);
    await d.hideCaption();
  },
};
