import type { ReactNode } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import TrigUseAdmin from "../TrigUseAdmin";

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("lucide-react", () => ({
  Plus: () => <span data-testid="icon-plus">+</span>,
  Pencil: () => <span data-testid="icon-pencil">✏</span>,
  Trash2: () => <span data-testid="icon-trash">🗑</span>,
  X: () => <span data-testid="icon-x">×</span>,
}));

vi.mock("../../../lib/api", () => ({
  fetchAllTrigUses: vi.fn(),
  createTrigUse: vi.fn(),
  updateTrigUse: vi.fn(),
  deleteTrigUse: vi.fn(),
  fetchTrigUseUsage: vi.fn(),
  requireAccessToken: vi.fn(
    async (
      getAccessTokenSilently: (options?: unknown) => Promise<string | undefined>,
      options?: unknown
    ) => await getAccessTokenSilently(options)
  ),
}));

import {
  fetchAllTrigUses,
  createTrigUse,
  updateTrigUse,
  deleteTrigUse,
  fetchTrigUseUsage,
} from "../../../lib/api";

const mockUseAuth0 = vi.mocked(useAuth0);
const mockFetchAll = vi.mocked(fetchAllTrigUses);
const mockCreate = vi.mocked(createTrigUse);
const mockUpdate = vi.mocked(updateTrigUse);
const mockDelete = vi.mocked(deleteTrigUse);
const mockUsage = vi.mocked(fetchTrigUseUsage);

const historicValues = [
  { id: 1, name: "none", description: null, sort_order: 0 },
  { id: 2, name: "Primary", description: "Primary triangulation", sort_order: 10 },
];

function renderPage(kind: "historic" | "current", queryClient = new QueryClient()) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return render(<TrigUseAdmin kind={kind} />, { wrapper });
}

describe("TrigUseAdmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth0.mockReturnValue({
      getAccessTokenSilently: vi.fn().mockResolvedValue("mock-token"),
      isAuthenticated: true,
      isLoading: false,
      loginWithRedirect: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);
    mockFetchAll.mockResolvedValue(historicValues);
  });

  it("lists the values for its kind", async () => {
    renderPage("historic");

    await waitFor(() => {
      expect(screen.getByText("Primary")).toBeInTheDocument();
    });
    expect(screen.getByText("Historic Use Management")).toBeInTheDocument();
    expect(screen.getByText("Primary triangulation")).toBeInTheDocument();
    expect(mockFetchAll).toHaveBeenCalledWith("historic", "mock-token");
  });

  it("uses the recent use wording and API kind", async () => {
    mockFetchAll.mockResolvedValue([]);
    renderPage("current");

    await waitFor(() => {
      expect(screen.getByText("Recent Use Management")).toBeInTheDocument();
    });
    expect(mockFetchAll).toHaveBeenCalledWith("current", "mock-token");
  });

  it("creates a value after the highest sort order and refreshes the dropdowns", async () => {
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    mockCreate.mockResolvedValue({
      id: 3,
      name: "Zero order",
      description: null,
      sort_order: 20,
    });
    renderPage("historic", queryClient);

    await waitFor(() => screen.getByText("Primary"));
    fireEvent.click(screen.getByRole("button", { name: /add value/i }));
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: " Zero order " },
    });
    expect(screen.getByLabelText(/sort order/i)).toHaveValue(20);
    fireEvent.click(screen.getByRole("button", { name: /create value/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        "historic",
        { name: "Zero order", description: "", sort_order: 20 },
        "mock-token"
      );
    });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["reference", "historicUse"],
    });
  });

  it("warns that a rename updates trigpoints", async () => {
    mockUpdate.mockResolvedValue({ ...historicValues[1], name: "First order" });
    renderPage("historic");

    await waitFor(() => screen.getByText("Primary"));
    fireEvent.click(screen.getByTitle("Edit Primary"));
    expect(screen.queryByText(/will be updated to/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: "First order" },
    });
    expect(screen.getByText(/will be updated to/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith(
        "historic",
        2,
        { name: "First order", description: "Primary triangulation", sort_order: 10 },
        "mock-token"
      );
    });
  });

  it("does not offer delete for a value in use", async () => {
    mockUsage.mockResolvedValue({ id: 2, usage_count: 6000 });
    renderPage("historic");

    await waitFor(() => screen.getByText("Primary"));
    fireEvent.click(screen.getByTitle("Delete Primary"));

    await waitFor(() => {
      expect(screen.getByText(/used by 6000 trigpoint\(s\)/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(mockDelete).not.toHaveBeenCalled();
  });
});
