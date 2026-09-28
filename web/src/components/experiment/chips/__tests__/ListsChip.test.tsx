import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ListsChip, type ListsChipProps } from "../ListsChip";
import { NO_LIST_FILTER } from "../listFilter";
import type { TrigListFull } from "../../../../hooks/useTrigLists";

function makeList(id: number, name: string, extra: Partial<TrigListFull> = {}): TrigListFull {
  return {
    id,
    owner_id: 1,
    owner_name: "me",
    name,
    description: null,
    metadata: null,
    visibility: "private",
    editability: "private",
    position: id * 10,
    item_count: id,
    is_default: false,
    created_at: "2026-01-01T00:00:00",
    updated_at: null,
    ...extra,
  };
}

// Deliberately out of order: the default list should still come first
const LISTS = [makeList(7, "Summer walks"), makeList(3, "Marked", { is_default: true, position: 90 })];

function renderChip(overrides: Partial<ListsChipProps> = {}) {
  const props: ListsChipProps = {
    lists: LISTS,
    value: NO_LIST_FILTER,
    onChange: vi.fn(),
    ...overrides,
  };
  render(<ListsChip {...props} />);
  return props;
}

const openChip = () => fireEvent.click(screen.getAllByRole("button", { name: /^Lists/ })[0]);

describe("ListsChip", () => {
  it("shows 'All' when off", () => {
    renderChip();
    expect(screen.getByText("All")).toBeInTheDocument();
  });

  it.each([
    [{ mode: "in", listIds: [3] }, "Marked"],
    [{ mode: "not_in", listIds: [3] }, "Not marked"],
    [{ mode: "in", listIds: [7] }, "In Summer walks"],
    [{ mode: "not_in", listIds: [3, 7] }, "Not in 2 lists"],
    [{ mode: "in", listIds: [] }, "Pick a list"],
  ] as const)("summarises %o as %s", (value, summary) => {
    renderChip({ value: { ...value, listIds: [...value.listIds] } });
    expect(screen.getByText(summary)).toBeInTheDocument();
  });

  it("starts from the Marked list when switching on", () => {
    const { onChange } = renderChip();
    openChip();
    fireEvent.click(screen.getByRole("radio", { name: "Not in" }));
    expect(onChange).toHaveBeenCalledWith({ mode: "not_in", listIds: [3] });
  });

  it("keeps the ticked lists when switching between in and not in", () => {
    const { onChange } = renderChip({ value: { mode: "in", listIds: [7] } });
    openChip();
    fireEvent.click(screen.getByRole("radio", { name: "Not in" }));
    expect(onChange).toHaveBeenCalledWith({ mode: "not_in", listIds: [7] });
  });

  it("switches to 'in' when a list is ticked while off", () => {
    const { onChange } = renderChip();
    openChip();
    fireEvent.click(screen.getByRole("checkbox", { name: "Summer walks" }));
    expect(onChange).toHaveBeenCalledWith({ mode: "in", listIds: [7] });
  });

  it("lists the default list first", () => {
    renderChip();
    openChip();
    const names = screen.getAllByRole("checkbox").map((box) => box.getAttribute("aria-label"));
    expect(names).toEqual(["Marked", "Summer walks"]);
  });

  it("explains how to start a list when the user has none", () => {
    renderChip({ lists: [] });
    openChip();
    expect(screen.getByText(/Star a trigpoint to start your Marked list/)).toBeInTheDocument();
  });
});
