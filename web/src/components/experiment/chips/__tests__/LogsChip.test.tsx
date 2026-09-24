import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LogsChip, type LogsChipProps } from "../LogsChip";

const CONDITIONS = [
  { code: "G", name: "Good", icon_file: "c_good.png", sort_order: 10 },
  { code: "M", name: "Moved", icon_file: "c_toppled.png", sort_order: 70 },
  { code: "Z", name: "Not logged", icon_file: "c_unknown.png", sort_order: 130 },
];
const ALL_CODES = CONDITIONS.map((c) => c.code);

vi.mock("../../../../hooks/useReferenceData", () => ({
  useConditions: () => ({ data: CONDITIONS, isLoading: false, isError: false }),
}));

vi.mock("../../../../hooks/useUserSearch", () => ({
  useUserSearch: (query: string) => ({
    isLoading: false,
    data:
      query.length >= 2
        ? [{ id: 42, name: "alice", stats: { total_logs: 5, total_trigs_logged: 1234, total_photos: 0 } }]
        : [],
  }),
}));

function renderChip(overrides: Partial<LogsChipProps> = {}) {
  const props: LogsChipProps = {
    selectedLoggedConditions: [...ALL_CODES],
    showNotLogged: true,
    onToggleLoggedCondition: vi.fn(),
    onToggleNotLogged: vi.fn(),
    onSelectAllLogged: vi.fn(),
    onSelectNoneLogged: vi.fn(),
    isAuthenticated: true,
    logUser: null,
    onLogUserChange: vi.fn(),
    ...overrides,
  };
  render(<LogsChip {...props} />);
  return props;
}

const openChip = () => fireEvent.click(screen.getAllByRole("button", { name: /^Logs/ })[0]);

describe("LogsChip", () => {
  it("asks signed-out visitors to pick a user", () => {
    renderChip({ isAuthenticated: false });
    expect(screen.getByText("Pick a user")).toBeInTheDocument();
    openChip();
    expect(screen.getByText("Pick a user to filter by their logs.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Me" })).not.toBeInTheDocument();
  });

  it("names the chosen user in the summary and options", () => {
    renderChip({ logUser: { id: 42, name: "alice" }, showNotLogged: false });
    expect(screen.getByText("Logged by alice")).toBeInTheDocument();
    openChip();
    expect(screen.getByText("Not logged by alice")).toBeInTheDocument();
  });

  it("picks a user from the search results", () => {
    const props = renderChip();
    openChip();
    fireEvent.change(screen.getByLabelText("Find a user"), { target: { value: "ali" } });
    fireEvent.click(screen.getByRole("button", { name: /alice/ }));
    expect(props.onLogUserChange).toHaveBeenCalledWith({ id: 42, name: "alice" });
  });

  it("goes back to the signed-in user with Me", () => {
    const props = renderChip({ logUser: { id: 42, name: "alice" } });
    openChip();
    fireEvent.click(screen.getByRole("button", { name: "Me" }));
    expect(props.onLogUserChange).toHaveBeenCalledWith(null);
  });

  it("lists every condition from the conditions API", () => {
    renderChip({ selectedLoggedConditions: ["G"] });
    openChip();
    fireEvent.click(screen.getByRole("button", { name: "Show logged conditions" }));
    expect(screen.getByText("Moved")).toBeInTheDocument();
    expect(screen.getByText("Not logged")).toBeInTheDocument();
    expect(screen.getByText("(1/3)")).toBeInTheDocument();
  });
});
