import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ConnectedAppsPanel from "../ConnectedAppsPanel";

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({
    isAuthenticated: true,
    getAccessTokenSilently: vi.fn().mockResolvedValue("test-token"),
  }),
}));

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../../../lib/api", async () => {
  const actual = await vi.importActual("../../../lib/api");
  return {
    ...actual,
    authenticatedGet: vi.fn(),
    authenticatedDelete: vi.fn(),
  };
});

import { authenticatedGet, authenticatedDelete } from "../../../lib/api";

const mockApps = {
  apps: [
    {
      grant_id: "gnt_pillarpoint",
      client_id: "client_abc",
      client_name: "tuk-pillarpoint",
      audience: "https://api.trigpointing.me/",
      scopes: ["openid", "profile", "offline_access"],
    },
    {
      grant_id: "gnt_unnamed",
      client_id: "client_xyz",
      client_name: null,
      audience: "https://api.trigpointing.me/",
      scopes: [],
    },
  ],
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("ConnectedAppsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an empty state when no applications are authorised", async () => {
    vi.mocked(authenticatedGet).mockResolvedValue({ apps: [] });

    render(<ConnectedAppsPanel />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(/haven't authorised any applications/i),
    ).toBeInTheDocument();
  });

  it("lists authorised applications with readable scope labels", async () => {
    vi.mocked(authenticatedGet).mockResolvedValue(mockApps);

    render(<ConnectedAppsPanel />, { wrapper: createWrapper() });

    expect(await screen.findByText("tuk-pillarpoint")).toBeInTheDocument();
    // Unnamed client falls back to its client_id
    expect(screen.getByText("client_xyz")).toBeInTheDocument();
    // Scope labels are humanised
    expect(screen.getByText("Sign in")).toBeInTheDocument();
    expect(screen.getByText("Stay signed in")).toBeInTheDocument();
  });

  it("shows an error message when loading fails", async () => {
    vi.mocked(authenticatedGet).mockRejectedValue(new Error("boom"));

    render(<ConnectedAppsPanel />, { wrapper: createWrapper() });

    expect(
      await screen.findByText(/failed to load connected applications/i),
    ).toBeInTheDocument();
  });

  it("revokes access after confirmation", async () => {
    vi.mocked(authenticatedGet).mockResolvedValue(mockApps);
    vi.mocked(authenticatedDelete).mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ConnectedAppsPanel />, { wrapper: createWrapper() });

    const revokeButtons = await screen.findAllByRole("button", {
      name: /revoke/i,
    });
    await userEvent.click(revokeButtons[0]);

    await waitFor(() => {
      expect(authenticatedDelete).toHaveBeenCalledWith(
        expect.stringContaining("/v1/users/me/connected-apps/gnt_pillarpoint"),
        expect.any(Function),
      );
    });
  });

  it("does not revoke when confirmation is cancelled", async () => {
    vi.mocked(authenticatedGet).mockResolvedValue(mockApps);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<ConnectedAppsPanel />, { wrapper: createWrapper() });

    const revokeButtons = await screen.findAllByRole("button", {
      name: /revoke/i,
    });
    await userEvent.click(revokeButtons[0]);

    expect(authenticatedDelete).not.toHaveBeenCalled();
  });
});
