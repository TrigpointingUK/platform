import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
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
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    );

    expect(
      screen.getByRole("heading", { name: /Trigpointing members/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: /Sort by/i })
    ).toHaveValue("trigs");
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
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
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
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    );

    expect(
      screen.getByText(/Loading the community directory/i)
    ).toBeInTheDocument();
  });
});


