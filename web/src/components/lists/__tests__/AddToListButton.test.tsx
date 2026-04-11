import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import AddToListButton from "../AddToListButton";

const mockMutate = vi.fn();
const mockToggleItemMutate = vi.fn();
const mockCreateMutate = vi.fn();

const mockLists = [
  {
    id: 1,
    owner_id: 10,
    name: "Marked",
    description: null,
    metadata: null,
    visibility: "private",
    editability: "private",
    position: 1000,
    item_count: 3,
    is_default: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: 2,
    owner_id: 10,
    name: "Favourites",
    description: "My favourite trigs",
    metadata: null,
    visibility: "public",
    editability: "private",
    position: 2000,
    item_count: 7,
    is_default: false,
    created_at: "2025-01-02T00:00:00Z",
    updated_at: null,
  },
];

const mockMemberships = [{ trig_id: 42, list_ids: [1] }];

vi.mock("../../../hooks/useTrigLists", () => ({
  useMyLists: () => ({ data: mockLists }),
  useTrigListMembership: () => ({ data: mockMemberships }),
  useToggleDefaultList: () => ({ mutate: mockMutate, isPending: false }),
  useToggleListItem: () => ({ mutate: mockToggleItemMutate, isPending: false }),
  useCreateList: () => ({ mutate: mockCreateMutate, isPending: false }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe("AddToListButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders star and dropdown toggle buttons", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    expect(screen.getByTitle("Remove from default list")).toBeInTheDocument();
    expect(screen.getByTitle("Add to other lists")).toBeInTheDocument();
  });

  it("shows filled star when trig is in default list", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    const starButton = screen.getByTitle("Remove from default list");
    const svg = starButton.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg?.getAttribute("fill")).toBe("currentColor");
  });

  it("calls toggleDefault on star click", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Remove from default list"));
    expect(mockMutate).toHaveBeenCalledTimes(1);
  });

  it("opens dropdown showing all lists with checkboxes", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Add to other lists"));

    expect(screen.getByText("Marked")).toBeInTheDocument();
    expect(screen.getByText("Favourites")).toBeInTheDocument();
  });

  it("shows default label on default list in dropdown", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Add to other lists"));

    expect(screen.getByText("default")).toBeInTheDocument();
  });

  it("calls toggleItem when dropdown list is clicked", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Add to other lists"));
    fireEvent.click(screen.getByText("Favourites"));

    expect(mockToggleItemMutate).toHaveBeenCalledWith({ listId: 2 });
  });

  it("shows 'View all lists' link in dropdown", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Add to other lists"));

    const link = screen.getByText("View all lists →");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/lists");
  });

  it("shows new list creation form in dropdown", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Add to other lists"));

    expect(screen.getByPlaceholderText("New list name...")).toBeInTheDocument();
    expect(screen.getByText("Add")).toBeInTheDocument();
  });

  it("creates a new list via the dropdown form", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Add to other lists"));

    const input = screen.getByPlaceholderText("New list name...");
    fireEvent.change(input, { target: { value: "My New List" } });

    const form = input.closest("form")!;
    fireEvent.submit(form);

    expect(mockCreateMutate).toHaveBeenCalledWith({ name: "My New List" });
  });

  it("closes dropdown on outside click", () => {
    render(
      <div>
        <div data-testid="outside">Outside</div>
        <AddToListButton trigId={42} />
      </div>,
      { wrapper: createWrapper() },
    );

    fireEvent.click(screen.getByTitle("Add to other lists"));
    expect(screen.getByText("Marked")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByTestId("outside"));
    expect(screen.queryByText("View all lists →")).not.toBeInTheDocument();
  });

  it("shows checked state for lists containing the trig", () => {
    render(<AddToListButton trigId={42} />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTitle("Add to other lists"));

    const markedButton = screen.getByText("Marked").closest("button")!;
    const checkbox = within(markedButton).getByText("", { selector: "span" });
    expect(checkbox.className).toContain("bg-trig-green-600");
  });
});
