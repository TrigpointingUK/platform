import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "../../contexts/ThemeContext";
import UsersPage from "../UsersPage";
import { useUsersDirectory } from "../../hooks/useUsersDirectory";
import { useAuth0 } from "@auth0/auth0-react";

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

vi.mock("../../hooks/useUsersDirectory", () => ({
  useUsersDirectory: vi.fn(),
  USERS_SORT_OPTIONS: [
    { label: "Trigpoints logged", value: "trigs" },
    { label: "Photos uploaded", value: "photos" },
    { label: "Logs recorded", value: "logs" },
    { label: "Joined date", value: "joined" },
    { label: "Alphabetical", value: "name" },
  ],
}));

vi.mock("../../components/layout/GlobalSearch", () => ({
  GlobalSearch: () => <div data-testid="global-search" />,
}));

const mockUseUsersDirectory = vi.mocked(useUsersDirectory);
const mockUseAuth0 = vi.mocked(useAuth0);

const defaultHookResponse = {
  data: {
    pages: [
      {
        items: [
          {
            id: 1,
            name: "Alice",
            member_since: "2023-01-01",
            stats: {
              total_logs: 5,
              total_trigs_logged: 5,
              total_photos: 2,
            },
            profile_path: "/profile/1",
          },
          {
            id: 2,
            name: "Bob",
            member_since: null,
            stats: {
              total_logs: 1,
              total_trigs_logged: 1,
              total_photos: 0,
            },
            profile_path: "/profile/2",
          },
        ],
        next_cursor: null,
        total: 2,
      },
    ],
    pageParams: [null],
  },
  isLoading: false,
  isError: false,
  error: null,
  fetchNextPage: vi.fn(),
  hasNextPage: false,
  isFetchingNextPage: false,
  refetch: vi.fn(),
};

describe("UsersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUsersDirectory.mockReturnValue(defaultHookResponse as never);
    mockUseAuth0.mockReturnValue({
      isAuthenticated: false,
      user: undefined,
      isLoading: false,
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      getAccessTokenSilently: vi.fn(),
    } as never);
  });

  it("renders community members", () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ThemeProvider>
    );

    expect(
      screen.getByRole("heading", { name: /The TrigpointingUK Community/i })
    ).toBeInTheDocument();
    
    // Names appear in both mobile and desktop layouts
    expect(screen.getAllByText("Alice").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Bob").length).toBeGreaterThanOrEqual(1);
    
    expect(
      screen.getByRole("columnheader", { name: /Trigpoints/i })
    ).toHaveAttribute("aria-sort", "descending");
    expect(
      screen.getByRole("columnheader", { name: /Name/i })
    ).toHaveAttribute("aria-sort", "none");
    expect(
      screen.getByRole("columnheader", { name: /Logs/i })
    ).toHaveAttribute("aria-sort", "none");

    // Stats links appear twice per user (mobile + desktop layouts)
    const trigLinks = screen.getAllByRole("link", { name: /Trigpoints/i });
    expect(trigLinks).toHaveLength(4); // 2 users × 2 layouts
    expect(trigLinks[0]).toHaveAttribute("href", "/profile/1/logs");
    expect(trigLinks[2]).toHaveAttribute("href", "/profile/2/logs");
    
    const photoLinks = screen.getAllByRole("link", { name: /Photos/i });
    expect(photoLinks).toHaveLength(4); // 2 users × 2 layouts
    expect(photoLinks[0]).toHaveAttribute("href", "/profile/1/photos");
    expect(photoLinks[2]).toHaveAttribute("href", "/profile/2/photos");
  });

  it("shows empty state when no results", () => {
    mockUseUsersDirectory.mockReturnValue({
      ...defaultHookResponse,
      data: {
        pages: [
          {
            items: [],
            next_cursor: null,
            total: 0,
          },
        ],
        pageParams: [null],
      },
    } as never);

    render(
      <ThemeProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ThemeProvider>
    );

    expect(
      screen.getByText(/No matches found/i)
    ).toBeInTheDocument();
  });

  it("shows loading state", () => {
    mockUseUsersDirectory.mockReturnValue({
      ...defaultHookResponse,
      isLoading: true,
    } as never);

    render(
      <ThemeProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ThemeProvider>
    );

    expect(
      screen.getByText(/Loading the community directory/i)
    ).toBeInTheDocument();
  });

  it("allows sorting via column headers", () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <UsersPage />
        </MemoryRouter>
      </ThemeProvider>
    );

    const nameHeader = screen.getByRole("columnheader", { name: /Name/i });
    fireEvent.click(nameHeader);
    expect(nameHeader).toHaveAttribute("aria-sort", "ascending");

    fireEvent.click(nameHeader);
    expect(nameHeader).toHaveAttribute("aria-sort", "descending");

    const logsHeader = screen.getByRole("columnheader", { name: /Logs/i });
    fireEvent.click(logsHeader);
    expect(logsHeader).toHaveAttribute("aria-sort", "descending");

    fireEvent.click(logsHeader);
    expect(logsHeader).toHaveAttribute("aria-sort", "ascending");
  });
});


