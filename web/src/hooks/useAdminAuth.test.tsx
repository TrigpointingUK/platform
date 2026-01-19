import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useAuth0 } from "@auth0/auth0-react";
import { useAdminAuth } from "./useAdminAuth";

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useLocation: () => ({ pathname: "/admin/attention/logs", search: "" }),
}));

const encodeBase64Url = (input: string): string => {
  // btoa expects binary; encode UTF-8 first.
  const base64 = btoa(unescape(encodeURIComponent(input)));
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
};

const makeJwt = (payload: Record<string, unknown>): string => {
  const header = encodeBase64Url(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = encodeBase64Url(JSON.stringify(payload));
  return `${header}.${body}.`;
};

describe("useAdminAuth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear the admin scope cache before each test
    sessionStorage.removeItem("trigpointing_admin_scope_verified");
  });

  afterEach(() => {
    vi.useRealTimers();
    // Clean up cache after each test
    sessionStorage.removeItem("trigpointing_admin_scope_verified");
  });

  it("reports admin scope when api:admin is present", async () => {
    const token = makeJwt({
      scope: "openid profile email api:write api:read-pii api:admin",
      permissions: [],
    });

    vi.mocked(useAuth0).mockReturnValue({
      user: { "https://trigpointing.uk/roles": ["api-admin"] },
      isAuthenticated: true,
      isLoading: false,
      getAccessTokenSilently: vi.fn().mockResolvedValue(token),
      loginWithRedirect: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    const { result } = renderHook(() => useAdminAuth());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hasAdminRole).toBe(true);
    expect(result.current.hasAdminScope).toBe(true);
  });

  it("does not get stuck in StrictMode when the first effect run is cancelled", async () => {
    const token = makeJwt({
      scope: "openid profile email api:write api:read-pii api:admin",
      permissions: [],
    });

    let resolveToken: ((value: string) => void) | null = null;
    const pendingToken = new Promise<string>((resolve) => {
      resolveToken = resolve;
    });
    const getAccessTokenSilently = vi.fn().mockReturnValue(pendingToken);

    vi.mocked(useAuth0).mockReturnValue({
      user: { "https://trigpointing.uk/roles": ["api-admin"] },
      isAuthenticated: true,
      isLoading: false,
      getAccessTokenSilently,
      loginWithRedirect: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <React.StrictMode>{children}</React.StrictMode>
    );

    const { result } = renderHook(() => useAdminAuth(), { wrapper });

    // Initial state should be loading while the token promise is pending
    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      // Resolve after render so the first StrictMode effect run has been cleaned up.
      resolveToken?.(token);
      await pendingToken;
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false), {
      timeout: 2000,
    });
    expect(result.current.hasAdminScope).toBe(true);
  });
});


