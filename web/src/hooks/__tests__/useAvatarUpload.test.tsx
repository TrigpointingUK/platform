import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock Auth0 before importing the hook
const mockGetAccessTokenSilently = vi.fn();
const mockLoginWithRedirect = vi.fn();

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({
    getAccessTokenSilently: mockGetAccessTokenSilently,
    loginWithRedirect: mockLoginWithRedirect,
  }),
}));

vi.mock("../../lib/authenticatedFetch", () => ({
  AuthenticationError: class AuthenticationError extends Error {
    public readonly code: string;
    public readonly status?: number;
    constructor(code: string, message: string, status?: number) {
      super(message);
      this.name = "AuthenticationError";
      this.code = code;
      this.status = status;
    }
  },
}));

import { useAvatarUpload } from "../useAvatarUpload";
import { AuthenticationError } from "../../lib/authenticatedFetch";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("useAvatarUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockGetAccessTokenSilently.mockResolvedValue("test-token");
    // Default: successful fetch
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            avatar_url:
              "https://trigpointinguk-avatars.s3.amazonaws.com/U00001.jpg?v=1234567890",
          }),
      })
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("should request a fresh Auth0 token with cacheMode off", async () => {
    const { result } = renderHook(() => useAvatarUpload(), {
      wrapper: createWrapper(),
    });

    const blob = new Blob(["image"], { type: "image/jpeg" });

    await act(async () => {
      await result.current.mutateAsync(blob);
    });

    expect(mockGetAccessTokenSilently).toHaveBeenCalledWith({
      cacheMode: "off",
    });
  });

  it("should POST FormData to the avatar endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ avatar_url: "https://example.com/a.jpg?v=1" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { result } = renderHook(() => useAvatarUpload(), {
      wrapper: createWrapper(),
    });

    const blob = new Blob(["image"], { type: "image/jpeg" });

    await act(async () => {
      await result.current.mutateAsync(blob);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/v1/users/me/avatar");
    expect(options.method).toBe("POST");
    expect(options.headers.Authorization).toBe("Bearer test-token");
    expect(options.body).toBeInstanceOf(FormData);
  });

  it("should return the avatar_url from the API response", async () => {
    const expectedUrl =
      "https://trigpointinguk-avatars.s3.amazonaws.com/U00042.jpg?v=9999";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ avatar_url: expectedUrl }),
      })
    );

    const { result } = renderHook(() => useAvatarUpload(), {
      wrapper: createWrapper(),
    });

    let data: { avatar_url: string } | undefined;
    await act(async () => {
      data = await result.current.mutateAsync(
        new Blob(["img"], { type: "image/jpeg" })
      );
    });

    expect(data?.avatar_url).toBe(expectedUrl);
  });

  it("should schedule an Auth0 token refresh 2 s after success", async () => {
    const { result } = renderHook(() => useAvatarUpload(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync(
        new Blob(["img"], { type: "image/jpeg" })
      );
    });

    // First call is in mutationFn for the upload itself
    expect(mockGetAccessTokenSilently).toHaveBeenCalledTimes(1);

    // Advance past the 2 s setTimeout in onSuccess
    await act(async () => {
      vi.advanceTimersByTime(2500);
    });

    // Second call is the deferred Auth0 refresh
    expect(mockGetAccessTokenSilently).toHaveBeenCalledTimes(2);
    expect(mockGetAccessTokenSilently).toHaveBeenLastCalledWith({
      cacheMode: "off",
    });
  });

  it("should not fail if the deferred Auth0 refresh rejects", async () => {
    // First call succeeds (mutationFn), second rejects (setTimeout)
    mockGetAccessTokenSilently
      .mockResolvedValueOnce("test-token")
      .mockRejectedValueOnce(new Error("Auth0 down"));

    const { result } = renderHook(() => useAvatarUpload(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync(
        new Blob(["img"], { type: "image/jpeg" })
      );
    });

    // Should not throw even when the deferred refresh fails
    await act(async () => {
      vi.advanceTimersByTime(2500);
    });

    expect(mockGetAccessTokenSilently).toHaveBeenCalledTimes(2);
  });

  it("should throw on non-OK HTTP responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: "Bad Request",
        text: () => Promise.resolve("File too large"),
      })
    );

    const { result } = renderHook(() => useAvatarUpload(), {
      wrapper: createWrapper(),
    });

    await expect(
      act(async () => {
        await result.current.mutateAsync(
          new Blob(["img"], { type: "image/jpeg" })
        );
      })
    ).rejects.toThrow("HTTP 400");
  });

  it("should redirect to login on AuthenticationError", async () => {
    // waitFor relies on real setTimeout, so switch back for this test
    vi.useRealTimers();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new AuthenticationError("token_expired", "Expired"))
    );

    const { result } = renderHook(() => useAvatarUpload(), {
      wrapper: createWrapper(),
    });

    try {
      await act(async () => {
        await result.current.mutateAsync(
          new Blob(["img"], { type: "image/jpeg" })
        );
      });
    } catch {
      // Expected to throw
    }

    await waitFor(() => {
      expect(mockLoginWithRedirect).toHaveBeenCalledWith({
        appState: { returnTo: window.location.pathname },
      });
    });
  });
});
