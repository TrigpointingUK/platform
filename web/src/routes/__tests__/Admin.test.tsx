import type { ReactNode } from "react";
import { describe, expect, it, beforeEach, vi, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { useAuth0 } from "@auth0/auth0-react";
import Admin from "../Admin";

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

vi.mock("../../components/layout/Layout", () => ({
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

const mockUseAuth0 = vi.mocked(useAuth0);

const baseScopes = "openid profile email api:write api:read-pii offline_access";

const createToken = (payload: Record<string, unknown>) => {
  const encodeSegment = (input: Record<string, unknown>) => {
    const json = JSON.stringify(input);

    if (typeof globalThis.btoa === "function") {
      return globalThis
        .btoa(json)
        .replace(/=/g, "")
        .replace(/\+/g, "-")
        .replace(/\//g, "_");
    }

    const nodeBuffer = (globalThis as { Buffer?: { from(data: string, encoding?: string): { toString(encoding: string): string } } }).Buffer;
    if (nodeBuffer) {
      return nodeBuffer
        .from(json, "utf8")
        .toString("base64")
        .replace(/=/g, "")
        .replace(/\+/g, "-")
        .replace(/\//g, "_");
    }

    throw new Error("Unable to base64-encode token segment in test environment.");
  };

  return `${encodeSegment({ alg: "HS256", typ: "JWT" })}.${encodeSegment(payload)}.signature`;
};

describe("Admin route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();

    mockUseAuth0.mockReturnValue({
      user: undefined,
      getAccessTokenSilently: vi.fn(),
      loginWithRedirect: vi.fn(),
      isLoading: false,
      isAuthenticated: false,
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders access denied for users without the api-admin role", () => {
    mockUseAuth0.mockReturnValue({
      user: {
        name: "Test User",
        "https://trigpointing.uk/roles": ["member"],
      },
      getAccessTokenSilently: vi.fn(),
      loginWithRedirect: vi.fn(),
      isLoading: false,
      isAuthenticated: true,
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    render(<Admin />);

    expect(screen.getByText("Access Denied")).toBeInTheDocument();
    expect(screen.getByText("You do not have permission to access the admin area.")).toBeInTheDocument();
  });

  it("displays the admin dashboard when the api:admin scope is present", async () => {
    const tokenWithAdminScope = createToken({
      scope: `${baseScopes} api:admin`,
    });
    const getAccessTokenSilently = vi.fn().mockResolvedValue(tokenWithAdminScope);
    const loginWithRedirect = vi.fn();

    mockUseAuth0.mockReturnValue({
      user: {
        name: "Admin User",
        "https://trigpointing.uk/roles": ["api-admin"],
      },
      getAccessTokenSilently,
      loginWithRedirect,
      isLoading: false,
      isAuthenticated: true,
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    render(<Admin />);

    await waitFor(() => {
      expect(getAccessTokenSilently).toHaveBeenCalled();
    });

    expect(screen.getByText("Admin Dashboard")).toBeInTheDocument();
    expect(loginWithRedirect).not.toHaveBeenCalled();
  });

  it("triggers re-authentication when api:admin scope is missing despite the permission", async () => {
    const tokenWithoutAdminScope = createToken({
      scope: baseScopes,
      permissions: ["api:admin"],
    });
    const getAccessTokenSilently = vi.fn().mockResolvedValue(tokenWithoutAdminScope);
    const loginWithRedirect = vi.fn().mockResolvedValue(undefined);

    mockUseAuth0.mockReturnValue({
      user: {
        name: "Admin User",
        "https://trigpointing.uk/roles": ["api-admin"],
      },
      getAccessTokenSilently,
      loginWithRedirect,
      isLoading: false,
      isAuthenticated: true,
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    render(<Admin />);

    await waitFor(() => {
      expect(getAccessTokenSilently).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(loginWithRedirect).toHaveBeenCalledTimes(1);
    });

    const [[options]] = loginWithRedirect.mock.calls;
    expect(options.authorizationParams?.scope).toContain("api:admin");
    expect(options.authorizationParams?.prompt).toBe("consent");
    expect(options.appState).toEqual({ returnTo: "/admin" });
    expect(sessionStorage.getItem("auth0_returnTo")).toBe("/admin");
    expect(screen.getByText("Admin access requires re-authentication.")).toBeInTheDocument();
  });

  it("requests interactive login when Auth0 returns a consent error", async () => {
    const getAccessTokenSilently = vi.fn().mockRejectedValue({ error: "consent_required" });
    const loginWithRedirect = vi.fn().mockResolvedValue(undefined);

    mockUseAuth0.mockReturnValue({
      user: {
        name: "Admin User",
        "https://trigpointing.uk/roles": ["api-admin"],
      },
      getAccessTokenSilently,
      loginWithRedirect,
      isLoading: false,
      isAuthenticated: true,
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    render(<Admin />);

    await waitFor(() => {
      expect(getAccessTokenSilently).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(loginWithRedirect).toHaveBeenCalledTimes(1);
    });

    expect(sessionStorage.getItem("auth0_returnTo")).toBe("/admin");
  });

  it("forces re-authentication when Auth0 returns an invalid_grant missing scope error", async () => {
    const getAccessTokenSilently = vi
      .fn()
      .mockRejectedValue({ error: "invalid_grant", error_description: "Missing required scope api:admin" });
    const loginWithRedirect = vi.fn().mockResolvedValue(undefined);

    mockUseAuth0.mockReturnValue({
      user: {
        name: "Admin User",
        "https://trigpointing.uk/roles": ["api-admin"],
      },
      getAccessTokenSilently,
      loginWithRedirect,
      isLoading: false,
      isAuthenticated: true,
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    render(<Admin />);

    await waitFor(() => {
      expect(getAccessTokenSilently).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(loginWithRedirect).toHaveBeenCalledTimes(1);
    });
  });

  it("allows admins to search for a user and trigger migration", async () => {
    const tokenWithAdminScope = createToken({
      scope: `${baseScopes} api:admin`,
    });
    const getAccessTokenSilently = vi.fn().mockResolvedValue(tokenWithAdminScope);
    const loginWithRedirect = vi.fn();

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input.toString();

        if (url.includes("/v1/admin/legacy-migration/users")) {
          const body = {
            items: [
              {
                id: 1,
                name: "alice",
                email: "alice@example.com",
                email_valid: "Y",
                auth0_user_id: null,
                has_auth0_account: false,
              },
            ],
          };
          return Promise.resolve(
            new Response(JSON.stringify(body), {
              status: 200,
              headers: { "Content-Type": "application/json" },
            })
          );
        }

        if (url.includes("/v1/admin/legacy-migration/migrate")) {
          const payload = {
            user_id: 1,
            username: "alice",
            email: "new-email@example.com",
            auth0_user_id: "auth0|alice123",
            message:
              'Hi alice! Your account has been migrated to the new login system. In order to choose a password, please click "login" in the top-right corner of the Trigpointing.uk homepage, click "Can\'t log in to your account?", enter "new-email@example.com" and click continue. Within a few minutes you should receive an email from contact@trigpointing.uk, containing a link which will enable you to set a password.',
          };
          return Promise.resolve(
            new Response(JSON.stringify(payload), {
              status: 200,
              headers: { "Content-Type": "application/json" },
            })
          );
        }

        return Promise.reject(new Error(`Unexpected request: ${url}`));
      });

    mockUseAuth0.mockReturnValue({
      user: {
        name: "Admin User",
        "https://trigpointing.uk/roles": ["api-admin"],
      },
      getAccessTokenSilently,
      loginWithRedirect,
      isLoading: false,
      isAuthenticated: true,
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    try {
      render(<Admin />);

      // Initial scope verification
      await waitFor(() => {
        expect(getAccessTokenSilently).toHaveBeenCalled();
      });

      const toggleButton = await screen.findByRole("button", {
        name: /Legacy User Migration/i,
      });
      fireEvent.click(toggleButton);

      const searchInput = screen.getByLabelText("Search legacy users");
      fireEvent.change(searchInput, { target: { value: "ali" } });

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("/v1/admin/legacy-migration/users"),
          expect.objectContaining({
            method: "GET",
          })
        );
      });

      const select = screen.getByLabelText("Matching users");
      await waitFor(() => {
        expect(screen.getByText("alice — alice@example.com")).toBeInTheDocument();
      });

      fireEvent.change(select, { target: { value: "1" } });

      const emailInput = screen.getByLabelText("Email address");
      expect(emailInput).toHaveValue("alice@example.com");

      fireEvent.change(emailInput, { target: { value: "new-email@example.com" } });

      const migrateButton = screen.getByRole("button", { name: "Migrate" });
      expect(migrateButton).not.toBeDisabled();

      fireEvent.click(migrateButton);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("/v1/admin/legacy-migration/migrate"),
          expect.objectContaining({
            method: "POST",
          })
        );
      });

      const replyTextarea = (await screen.findByLabelText(
        "Reply template for the user"
      )) as HTMLTextAreaElement;
      expect(replyTextarea.value).toContain("Hi alice!");
      expect(replyTextarea.value).toContain("new-email@example.com");

      await waitFor(() =>
        expect(
          screen.queryByText(/already has an Auth0 user identifier/i)
        ).not.toBeInTheDocument()
      );
    } finally {
      fetchMock.mockRestore();
    }
  });
});

