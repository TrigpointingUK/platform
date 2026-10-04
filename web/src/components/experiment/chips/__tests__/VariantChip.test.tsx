import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { VariantChip } from "../VariantChip";
import { VARIANT_NOT_RECORDED } from "../../../../lib/trigVariants";

const DETECTOR = {
  code: "DETECTOR",
  name: "Detector material",
  values: [
    { value: "CONCRETE_RING", label: "Concrete ring" },
    { value: "BRONZE_RING", label: "Bronze ring" },
  ],
};
const DESIGN = { code: "DESIGN", name: "Pillar design", values: [{ value: "HOTINE", label: "Hotine" }] };
const ALL = ["CONCRETE_RING", "BRONZE_RING", VARIANT_NOT_RECORDED];

const renderChip = (groups = [DETECTOR], selectedValues: string[] = ALL) => {
  const handlers = { onToggle: vi.fn(), onSelectAll: vi.fn(), onSelectNone: vi.fn() };
  render(<VariantChip groups={groups} selectedValues={selectedValues} {...handlers} />);
  return handlers;
};
const chipButton = (name: RegExp) => screen.getAllByRole("button", { name })[0];

describe("VariantChip", () => {
  it("is named after its only group and summarises everything ticked as All", () => {
    renderChip();
    expect(chipButton(/Detector material/)).toHaveTextContent("All");
  });

  it("summarises nothing ticked as None", () => {
    renderChip([DETECTOR], []);
    expect(chipButton(/Detector material/)).toHaveTextContent("None");
  });

  it("shows the only selected option's label, including not recorded", () => {
    renderChip([DETECTOR], ["BRONZE_RING"]);
    expect(chipButton(/Detector material/)).toHaveTextContent("Bronze ring");
  });

  it("offers All, None and Not recorded in the popover", () => {
    const handlers = renderChip([DETECTOR], ["CONCRETE_RING"]);
    fireEvent.click(chipButton(/Detector material/));
    fireEvent.click(screen.getByRole("button", { name: "All" }));
    expect(handlers.onSelectAll).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "None" }));
    expect(handlers.onSelectNone).toHaveBeenCalled();
    fireEvent.click(screen.getByText("Not recorded"));
    expect(handlers.onToggle).toHaveBeenCalledWith(VARIANT_NOT_RECORDED);
  });

  it("uses a generic name when offering several groups", () => {
    renderChip([DETECTOR, DESIGN]);
    expect(chipButton(/^Variant/)).toBeTruthy();
  });
});
