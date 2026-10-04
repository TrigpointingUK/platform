import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import VariantSelect from "../VariantSelect";
import type { TrigCategory } from "../../../hooks/useTrigTypes";

vi.mock("../../../hooks/useReferenceData", () => ({
  useVariantGroups: () => ({
    data: [
      {
        code: "DETECTOR",
        name: "Detector material",
        values: [
          { value: "CONCRETE_RING", label: "Concrete ring" },
          { value: "SCRAP_METAL", label: "Scrap metal" },
        ],
      },
    ],
  }),
}));

const type = (id: number, code: string, variant_group: string | null) => ({
  id,
  category_id: 3,
  code,
  name: code,
  description: null,
  wiki_url: null,
  sort_order: id,
  variant_group,
});

const CATEGORIES: TrigCategory[] = [
  {
    id: 3,
    code: "SURVEY_MARK",
    name: "Survey mark",
    description: null,
    wiki_url: null,
    sort_order: 30,
    types: [type(7, "BURIED_BLOCK", "DETECTOR"), type(8, "RIVET", null)],
  },
];

describe("VariantSelect", () => {
  it("renders nothing for a type without variants", () => {
    const { container } = render(
      <VariantSelect categories={CATEGORIES} typeId={8} value={null} onChange={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("offers the type's variants under the group's name, blank as not recorded", () => {
    const onChange = vi.fn();
    render(<VariantSelect categories={CATEGORIES} typeId={7} value={null} onChange={onChange} />);
    const select = screen.getByLabelText("Detector material");
    expect(screen.getByRole("option", { name: "Not recorded" })).toBeInTheDocument();

    fireEvent.change(select, { target: { value: "SCRAP_METAL" } });
    expect(onChange).toHaveBeenLastCalledWith("SCRAP_METAL");

    fireEvent.change(select, { target: { value: "" } });
    expect(onChange).toHaveBeenLastCalledWith(null);
  });
});
