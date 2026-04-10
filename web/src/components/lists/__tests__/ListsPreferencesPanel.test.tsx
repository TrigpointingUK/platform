import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import ListsPreferencesPanel from "../ListsPreferencesPanel";

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({
    isAuthenticated: true,
    getAccessTokenSilently: vi.fn().mockResolvedValue("test-token"),
  }),
}));

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));

const mockCreateMutate = vi.fn();
const mockDeleteMutate = vi.fn();
const mockUpdateMutate = vi.fn();
const mockReorderMutate = vi.fn();
const mockSetDefaultMutate = vi.fn();

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
    item_count: 5,
    is_default: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: 2,
    owner_id: 10,
    name: "Summer Plans",
    description: "Trigs to visit this summer",
    metadata: null,
    visibility: "public",
    editability: "private",
    position: 2000,
    item_count: 12,
    is_default: false,
    created_at: "2025-01-02T00:00:00Z",
    updated_at: null,
  },
];

vi.mock("../../../hooks/useTrigLists", () => ({
  useMyLists: () => ({ data: mockLists, isLoading: false }),
  useCreateList: () => ({ mutate: mockCreateMutate, isPending: false }),
  useDeleteList: () => ({ mutate: mockDeleteMutate }),
  useUpdateList: () => ({ mutate: mockUpdateMutate }),
  useReorderLists: () => ({ mutate: mockReorderMutate }),
  useSetDefaultList: () => ({ mutate: mockSetDefaultMutate }),
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

describe("ListsPreferencesPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the panel heading", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Trig Lists")).toBeInTheDocument();
  });

  it("renders 'View your lists' link", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const link = screen.getByText("View your lists →");
    expect(link.closest("a")).toHaveAttribute("href", "/lists");
  });

  it("renders all user lists with names and item counts", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Marked")).toBeInTheDocument();
    expect(screen.getByText("5 items")).toBeInTheDocument();
    expect(screen.getByText("Summer Plans")).toBeInTheDocument();
    expect(screen.getByText("12 items")).toBeInTheDocument();
  });

  it("shows 'default' badge on the default list", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("default")).toBeInTheDocument();
  });

  it("shows description for lists that have one", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Trigs to visit this summer")).toBeInTheDocument();
  });

  it("shows 'Make default' button for non-default lists", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const makeDefaultButtons = screen.getAllByText("Make default");
    expect(makeDefaultButtons.length).toBe(1);
  });

  it("calls setDefaultList when 'Make default' is clicked", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByText("Make default"));
    expect(mockSetDefaultMutate).toHaveBeenCalledWith(2);
  });

  it("links list tiles to /lists/:id", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const markedLink = screen.getByText("Marked").closest("a");
    expect(markedLink).toHaveAttribute("href", "/lists/1");

    const summerLink = screen.getByText("Summer Plans").closest("a");
    expect(summerLink).toHaveAttribute("href", "/lists/2");
  });

  it("renders new list creation form", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByPlaceholderText("New list name...")).toBeInTheDocument();
    expect(screen.getByText("Create")).toBeInTheDocument();
  });

  it("creates a new list via the form", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const input = screen.getByPlaceholderText("New list name...");
    fireEvent.change(input, { target: { value: "Winter Plans" } });

    const form = input.closest("form")!;
    fireEvent.submit(form);

    expect(mockCreateMutate).toHaveBeenCalledWith({ name: "Winter Plans" });
  });

  it("disables create button when name is empty", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const createButton = screen.getByText("Create");
    expect(createButton).toBeDisabled();
  });

  it("opens edit mode when edit button is clicked", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const editButtons = screen.getAllByTitle("Edit list");
    fireEvent.click(editButtons[0]);

    expect(screen.getByDisplayValue("Marked")).toBeInTheDocument();
    expect(screen.getByText("Save")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("saves edits when Save is clicked", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const editButtons = screen.getAllByTitle("Edit list");
    fireEvent.click(editButtons[0]);

    const nameInput = screen.getByDisplayValue("Marked");
    fireEvent.change(nameInput, { target: { value: "Renamed List" } });
    fireEvent.click(screen.getByText("Save"));

    expect(mockUpdateMutate).toHaveBeenCalledWith({
      listId: 1,
      data: { name: "Renamed List" },
    });
  });

  it("cancels edit mode on Cancel", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const editButtons = screen.getAllByTitle("Edit list");
    fireEvent.click(editButtons[0]);

    expect(screen.getByDisplayValue("Marked")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.queryByDisplayValue("Marked")).not.toBeInTheDocument();
    expect(screen.getByText("Marked")).toBeInTheDocument();
  });

  it("shows delete confirmation when delete is clicked", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const deleteButtons = screen.getAllByTitle("Delete list");
    fireEvent.click(deleteButtons[0]);

    expect(screen.getByText("Confirm")).toBeInTheDocument();
    expect(screen.getByText("No")).toBeInTheDocument();
  });

  it("deletes list on confirm", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const deleteButtons = screen.getAllByTitle("Delete list");
    fireEvent.click(deleteButtons[0]);
    fireEvent.click(screen.getByText("Confirm"));

    expect(mockDeleteMutate).toHaveBeenCalledWith(1);
  });

  it("cancels deletion on No", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const deleteButtons = screen.getAllByTitle("Delete list");
    fireEvent.click(deleteButtons[0]);
    fireEvent.click(screen.getByText("No"));

    expect(mockDeleteMutate).not.toHaveBeenCalled();
  });

  it("renders drag handles for reordering", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const dragHandles = screen.getAllByTitle("Drag to reorder");
    expect(dragHandles.length).toBe(2);
  });

  it("renders visibility and editability dropdowns", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    const labels = screen.getAllByText("Visible to:");
    expect(labels.length).toBe(2);

    const editLabels = screen.getAllByText("Editable by:");
    expect(editLabels.length).toBe(2);
  });

  it("hides admin-only options for non-admin users", () => {
    render(<ListsPreferencesPanel hasAdminRole={false} />, {
      wrapper: createWrapper(),
    });

    expect(screen.queryByText("Admins only")).not.toBeInTheDocument();
  });

  it("shows admin-only options for admin users", () => {
    render(<ListsPreferencesPanel hasAdminRole={true} />, {
      wrapper: createWrapper(),
    });

    const adminsOnlyOptions = screen.getAllByText("Admins only");
    expect(adminsOnlyOptions.length).toBeGreaterThan(0);
  });

  it("has the trig-lists id for hash scrolling", () => {
    const { container } = render(
      <ListsPreferencesPanel hasAdminRole={false} />,
      { wrapper: createWrapper() },
    );

    expect(container.querySelector("#trig-lists")).toBeInTheDocument();
  });
});
