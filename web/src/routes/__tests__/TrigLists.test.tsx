import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import TrigLists from "../TrigLists";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({}),
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
    item_count: 2,
    is_default: true,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: null,
  },
  {
    id: 2,
    owner_id: 10,
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

vi.mock("../../hooks/useTrigLists", () => ({
  useMyLists: () => ({ data: mockLists, isLoading: false }),
  useListItems: () => ({
    data: mockItems,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
    isLoading: false,
  }),
  useReorderItems: () => ({ mutate: mockReorderMutate }),
  useUpdateListItem: () => ({ mutate: mockUpdateItemMutate }),
}));

vi.mock("../../hooks/useUserProfile", () => ({
  useUserProfile: () => ({
    data: { prefs: { distance_ind: "K" } },
    isLoading: false,
  }),
}));

vi.mock("../../hooks/useDocumentTitle", () => ({
  useDocumentTitle: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/lists"]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe("TrigLists", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
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
});

describe("TrigLists - unauthenticated", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = false;
  });

  it("shows sign-in prompt when not authenticated", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TrigLists />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      screen.getByText("Sign in to view and manage your trig lists."),
    ).toBeInTheDocument();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });
});
