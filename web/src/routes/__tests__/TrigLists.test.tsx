import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import TrigLists from "../TrigLists";

const mockNavigate = vi.fn();
let mockParams: Record<string, string> = {};

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

let mockIsAuthenticated = true;
const mockLoginWithRedirect = vi.fn();

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({
    isAuthenticated: mockIsAuthenticated,
    getAccessTokenSilently: vi.fn().mockResolvedValue("test-token"),
    loginWithRedirect: mockLoginWithRedirect,
  }),
}));

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));

const mockReorderMutate = vi.fn();
const mockUpdateItemMutate = vi.fn();
const mockRemoveFromListMutate = vi.fn();

const mockLists = [
  {
    id: 1,
    owner_id: 10,
    owner_name: null,
    name: "Marked",
    description: null,
    metadata: null,
    visibility: "private",
    editability: "private",
    position: 1000,
    item_count: 2,
    is_default: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: 2,
    owner_id: 10,
    owner_name: null,
    name: "Favourites",
    description: null,
    metadata: null,
    visibility: "public",
    editability: "private",
    position: 2000,
    item_count: 0,
    is_default: false,
    created_at: "2025-01-02T00:00:00Z",
    updated_at: null,
  },
];

const mockItems = {
  pages: [
    {
      items: [
        {
          id: 100,
          list_id: 1,
          trig_id: 42,
          created_by: 10,
          updated_by: null,
          name: null,
          description: "Great views",
          metadata: null,
          position: 1000,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: null,
          trig: {
            id: 42,
            waypoint: "TP0042",
            name: "Test Trig Alpha",
            condition: "G",
            osgb_gridref: "TQ 12345 67890",
            wgs_lat: "51.5",
            wgs_long: "-0.1",
            wgs_height: 100,
            type_code: "PILLAR",
            type_name: "Pillar",
            category_code: "PILLAR",
            category_name: "Pillar",
            status_name: "Active",
            score: null,
          },
        },
        {
          id: 101,
          list_id: 1,
          trig_id: 43,
          created_by: 10,
          updated_by: null,
          name: null,
          description: null,
          metadata: null,
          position: 2000,
          created_at: "2025-01-02T00:00:00Z",
          updated_at: null,
          trig: {
            id: 43,
            waypoint: "TP0043",
            name: "Test Trig Beta",
            condition: "D",
            osgb_gridref: "TQ 54321 09876",
            wgs_lat: "51.6",
            wgs_long: "-0.2",
            wgs_height: 200,
            type_code: "PILLAR",
            type_name: "Pillar",
            category_code: "PILLAR",
            category_name: "Pillar",
            status_name: "Active",
            score: null,
          },
        },
      ],
      total: 2,
      has_more: false,
    },
  ],
  pageParams: [0],
};

const mockPublicList = {
  id: 50,
  owner_id: 99,
  owner_name: "Other User",
  name: "Shared Pillars",
  description: "A curated list of pillars",
  metadata: null,
  visibility: "public",
  editability: "private",
  position: 1000,
  item_count: 2,
  is_default: false,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: null,
};

const mockPublicEditableList = {
  ...mockPublicList,
  editability: "public",
};

let mockListDetailData: typeof mockPublicList | undefined;
let mockListDetailLoading = false;
let mockListDetailError: Error | null = null;
let mockCurrentUser: { id: number; name: string } | null = { id: 10, name: "Test User" };
let mockHasAdminRole = false;

vi.mock("../../hooks/useTrigLists", () => ({
  useMyLists: () => ({ data: mockLists, isLoading: false }),
  useListDetail: () => ({
    data: mockListDetailData,
    isLoading: mockListDetailLoading,
    error: mockListDetailError,
  }),
  useListItems: () => ({
    data: mockItems,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
    isLoading: false,
  }),
  useReorderItems: () => ({ mutate: mockReorderMutate }),
  useUpdateListItem: () => ({ mutate: mockUpdateItemMutate }),
  useRemoveFromList: () => ({ mutate: mockRemoveFromListMutate }),
}));

vi.mock("../../hooks/useUserProfile", () => ({
  useUserProfile: () => ({
    data: { prefs: { distance_ind: "K" } },
    isLoading: false,
  }),
}));

vi.mock("../../hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    data: mockCurrentUser,
    isLoading: false,
  }),
}));

vi.mock("../../hooks/useAdminAuth", () => ({
  useAdminAuth: () => ({
    hasAdminRole: mockHasAdminRole,
  }),
}));

vi.mock("../../hooks/useDocumentTitle", () => ({
  useDocumentTitle: vi.fn(),
}));

const createWrapper = (initialEntries = ["/lists"]) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe("TrigLists", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
    mockParams = {};
    mockListDetailData = undefined;
    mockListDetailLoading = false;
    mockListDetailError = null;
    mockCurrentUser = { id: 10, name: "Test User" };
    mockHasAdminRole = false;
  });

  it("renders page heading and description", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    expect(screen.getByText("Lists")).toBeInTheDocument();
    expect(
      screen.getByText("Browse your saved trigpoint collections."),
    ).toBeInTheDocument();
  });

  it("renders 'Manage lists' link to preferences", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const link = screen.getByText("Manage lists →");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/preferences#trig-lists");
  });

  it("renders list selector dropdown", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
  });

  it("shows default flag in list selector for default list", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const select = screen.getByRole("combobox");
    const options = Array.from(select.querySelectorAll("option"));
    const markedOption = options.find((o) => o.textContent?.includes("Marked"));
    expect(markedOption?.textContent).toContain("★ default");
  });

  it("does not show default flag for non-default lists", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const select = screen.getByRole("combobox");
    const options = Array.from(select.querySelectorAll("option"));
    const favOption = options.find((o) => o.textContent?.includes("Favourites"));
    expect(favOption?.textContent).not.toContain("★ default");
  });

  it("renders trig cards for items in the selected list", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    expect(screen.getByText("Test Trig Alpha")).toBeInTheDocument();
    expect(screen.getByText("Test Trig Beta")).toBeInTheDocument();
  });

  it("shows existing description as italic text", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    expect(screen.getByText("Great views")).toBeInTheDocument();
  });

  it("shows edit pencil icons for each item", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const editButtons = screen.getAllByTitle(/note/);
    expect(editButtons.length).toBe(2);
    expect(screen.getByTitle("Edit note")).toBeInTheDocument();
    expect(screen.getByTitle("Add note")).toBeInTheDocument();
  });

  it("opens inline editor when pencil icon is clicked", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const addNoteButton = screen.getByTitle("Add note");
    fireEvent.click(addNoteButton);

    expect(screen.getByPlaceholderText("Add a note...")).toBeInTheDocument();
    expect(screen.getByText("Save")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("saves description on Save click", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const addNoteButton = screen.getByTitle("Add note");
    fireEvent.click(addNoteButton);

    const textarea = screen.getByPlaceholderText("Add a note...");
    fireEvent.change(textarea, { target: { value: "New note text" } });
    fireEvent.click(screen.getByText("Save"));

    expect(mockUpdateItemMutate).toHaveBeenCalledWith({
      itemId: 101,
      data: { description: "New note text" },
    });
  });

  it("cancels editing on Cancel click", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const addNoteButton = screen.getByTitle("Add note");
    fireEvent.click(addNoteButton);

    expect(screen.getByPlaceholderText("Add a note...")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.queryByPlaceholderText("Add a note...")).not.toBeInTheDocument();
  });

  it("renders drag handles for reordering", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    const dragHandles = screen.getAllByTitle("Drag to reorder");
    expect(dragHandles.length).toBe(2);
  });

  describe("delete/remove button", () => {
    it("renders remove buttons for each item", () => {
      render(<TrigLists />, { wrapper: createWrapper() });

      const removeButtons = screen.getAllByTitle("Remove from list");
      expect(removeButtons.length).toBe(2);
    });

    it("calls removeFromList mutation when remove button is clicked", () => {
      render(<TrigLists />, { wrapper: createWrapper() });

      const removeButtons = screen.getAllByTitle("Remove from list");
      fireEvent.click(removeButtons[0]);

      expect(mockRemoveFromListMutate).toHaveBeenCalledWith({
        listId: 1,
        itemId: 100,
      });
    });

    it("calls removeFromList with correct item ID for second item", () => {
      render(<TrigLists />, { wrapper: createWrapper() });

      const removeButtons = screen.getAllByTitle("Remove from list");
      fireEvent.click(removeButtons[1]);

      expect(mockRemoveFromListMutate).toHaveBeenCalledWith({
        listId: 1,
        itemId: 101,
      });
    });
  });
});

describe("TrigLists - unauthenticated", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = false;
    mockParams = {};
    mockListDetailData = undefined;
    mockListDetailLoading = false;
    mockListDetailError = null;
    mockCurrentUser = null;
    mockHasAdminRole = false;
  });

  it("shows sign-in prompt when not authenticated and no list ID", () => {
    render(<TrigLists />, { wrapper: createWrapper() });

    expect(
      screen.getByText("Sign in to view and manage your trig lists."),
    ).toBeInTheDocument();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  it("does not show sign-in prompt when viewing a specific public list", () => {
    mockParams = { listId: "50" };
    mockListDetailData = mockPublicList;

    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(
      screen.queryByText("Sign in to view and manage your trig lists."),
    ).not.toBeInTheDocument();
  });

  it("renders public list content for unauthenticated users", () => {
    mockParams = { listId: "50" };
    mockListDetailData = mockPublicList;

    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getByText("Shared Pillars")).toBeInTheDocument();
    expect(screen.getByText("Other User")).toBeInTheDocument();
  });
});

describe("TrigLists - viewing another user's public list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
    mockParams = { listId: "50" };
    mockListDetailData = mockPublicList;
    mockListDetailLoading = false;
    mockListDetailError = null;
    mockCurrentUser = { id: 10, name: "Test User" };
    mockHasAdminRole = false;
  });

  it("shows list name as the page heading", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getByText("Shared Pillars")).toBeInTheDocument();
  });

  it("shows owner name", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getByText("Other User")).toBeInTheDocument();
  });

  it("shows list description", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getByText(/A curated list of pillars/)).toBeInTheDocument();
  });

  it("shows item count", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getByText(/2 trigpoints/)).toBeInTheDocument();
  });

  it("does not show list selector dropdown", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("does not show 'Manage lists' link", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.queryByText("Manage lists →")).not.toBeInTheDocument();
  });

  it("does not show drag handles in read-only mode", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.queryAllByTitle("Drag to reorder")).toHaveLength(0);
  });

  it("does not show edit note buttons in read-only mode", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.queryAllByTitle(/note/)).toHaveLength(0);
  });

  it("does not show remove buttons in read-only mode", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.queryAllByTitle("Remove from list")).toHaveLength(0);
  });

  it("still renders trig cards", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getByText("Test Trig Alpha")).toBeInTheDocument();
    expect(screen.getByText("Test Trig Beta")).toBeInTheDocument();
  });

  it("still shows existing descriptions in read-only mode", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getByText("Great views")).toBeInTheDocument();
  });
});

describe("TrigLists - viewing a publicly editable list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
    mockParams = { listId: "50" };
    mockListDetailData = mockPublicEditableList;
    mockListDetailLoading = false;
    mockListDetailError = null;
    mockCurrentUser = { id: 10, name: "Test User" };
    mockHasAdminRole = false;
  });

  it("shows drag handles when user can edit", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getAllByTitle("Drag to reorder")).toHaveLength(2);
  });

  it("shows edit note buttons when user can edit", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getAllByTitle(/note/)).toHaveLength(2);
  });

  it("shows remove buttons when user can edit", () => {
    render(<TrigLists />, { wrapper: createWrapper(["/lists/50"]) });

    expect(screen.getAllByTitle("Remove from list")).toHaveLength(2);
  });
});

describe("TrigLists - error states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
    mockCurrentUser = { id: 10, name: "Test User" };
    mockHasAdminRole = false;
    mockListDetailLoading = false;
  });

  it("shows not found message when direct list ID fails to load", () => {
    mockParams = { listId: "999" };
    mockListDetailData = undefined;
    mockListDetailError = new Error("Not found");

    render(<TrigLists />, { wrapper: createWrapper(["/lists/999"]) });

    expect(screen.getByText("List not found")).toBeInTheDocument();
    expect(
      screen.getByText("This list may not exist or may not be publicly visible."),
    ).toBeInTheDocument();
  });

  it("shows not found for unauthenticated user accessing private list", () => {
    mockIsAuthenticated = false;
    mockCurrentUser = null;
    mockParams = { listId: "999" };
    mockListDetailData = undefined;
    mockListDetailError = new Error("Not found");

    render(<TrigLists />, { wrapper: createWrapper(["/lists/999"]) });

    expect(screen.getByText("List not found")).toBeInTheDocument();
  });
});
