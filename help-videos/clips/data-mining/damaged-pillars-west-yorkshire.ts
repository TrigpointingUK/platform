import { LEEDS, type Clip } from "../../lib/clip.ts";
import { chip, option, popover, resultCount, TRIGS_V2 } from "../../lib/trigsV2.ts";

export const clip: Clip = {
  id: "damaged-pillars-west-yorkshire",
  section: "Data mining UK trigpoints",
  question: "How many damaged pillars are there in West Yorkshire?",
  path: TRIGS_V2,
  geolocation: LEEDS,
  async run(d) {
    const page = d.page;
    await d.caption("Type: choose just pillars", 300);
    await d.click(chip(page, "Type"));
    await d.click(popover(page, "Type").getByRole("button", { name: "None", exact: true }));
    await d.click(option(page, "Type", "Pillar"));
    await d.click(chip(page, "Type"));

    await d.caption("Condition: only those last logged as damaged", 300);
    await d.click(chip(page, "Condition"));
    await d.click(popover(page, "Condition").getByRole("button", { name: "None", exact: true }));
    await d.click(option(page, "Condition", "Damaged"));
    await d.click(chip(page, "Condition"));

    await d.caption("Area: pick the county", 300);
    await d.click(chip(page, "Area"));
    const areaType = popover(page, "Area").getByRole("combobox");
    await d.hover(areaType, 300);
    await areaType.selectOption("Ceremonial County");
    await d.pause(500);
    await d.caption("Sorting by Nearest puts local areas at the top", 300);
    await d.click(popover(page, "Area").getByRole("button", { name: "Nearest" }));
    await d.click(option(page, "Area", "West Yorkshire"));
    await d.click(chip(page, "Area"));
    await d.settle();

    const count = (await resultCount(page).innerText()).trim();
    await d.hover(resultCount(page), 200);
    await d.caption(`Answer: ${count} damaged ${count === "1" ? "pillar" : "pillars"} in West Yorkshire`, 300);
    await d.highlight(resultCount(page), 2600);
    await d.hideCaption();
  },
};
