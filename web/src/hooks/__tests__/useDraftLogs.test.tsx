import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCreateDraftLog } from "../useCreateDraftLog";
import { usePublishLog } from "../usePublishLog";
import { useCancelDraftLog } from "../useCancelDraftLog";

// Mock Auth0
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({
    getAccessTokenSilently: vi.fn().mockResolvedValue("mock-token"),
    loginWithRedirect: vi.fn(),
    isAuthenticated: true,
  }),
}));

// Mock fetch globally
const mockFetch = vi.fn();
(globalThis as unknown as { fetch: typeof fetch }).fetch = mockFetch;

// Create a wrapper with QueryClient
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

describe("useCreateDraftLog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should create a draft log when mutate is called", async () => {
    const mockDraftLog = {
      id: 123,
      trig_id: 456,
      user_id: 1,
      status: "D",
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockDraftLog),
    });

    const { result } = renderHook(() => useCreateDraftLog(456), {
      wrapper: createWrapper(),
    });

    // Trigger the mutation
    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockDraftLog);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/logs?trig_id=456&draft=true"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer mock-token",
        }),
      })
    );
  });

  it("should handle errors when creating draft fails", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      text: () => Promise.resolve("Server error"),
    });

    const { result } = renderHook(() => useCreateDraftLog(456), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe("usePublishLog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should publish a draft log when mutate is called", async () => {
    const mockPublishedLog = {
      id: 123,
      trig_id: 456,
      user_id: 1,
      status: "P",
      date: "2024-06-15",
      time: "14:30:00",
      condition: "G",
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockPublishedLog),
    });

    const { result } = renderHook(() => usePublishLog(123, 456), {
      wrapper: createWrapper(),
    });

    // Trigger the mutation with log data
    result.current.mutate({
      date: "2024-06-15",
      time: "14:30:00",
      condition: "G",
      comment: "Test comment",
      score: 8,
      fb_number: "",
      source: "W",
      osgb_eastings: 513700,
      osgb_northings: 205500,
      osgb_gridref: "TL 137 055",
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPublishedLog);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/logs/123/publish"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer mock-token",
          "Content-Type": "application/json",
        }),
      })
    );
  });

  it("should handle duplicate log error", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 409,
      statusText: "Conflict",
      json: () =>
        Promise.resolve({
          detail: {
            message: "You already have a log for this trigpoint on this date",
            existing_log_id: 999,
          },
        }),
    });

    const { result } = renderHook(() => usePublishLog(123, 456), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      date: "2024-06-15",
      time: "14:30:00",
      condition: "G",
      comment: "Test comment",
      score: 8,
      fb_number: "",
      source: "W",
      osgb_eastings: 513700,
      osgb_northings: 205500,
      osgb_gridref: "TL 137 055",
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe("useCancelDraftLog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should delete a draft log when mutate is called", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const { result } = renderHook(() => useCancelDraftLog(123, 456), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/logs/123"),
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({
          Authorization: "Bearer mock-token",
        }),
      })
    );
  });

  it("should throw error when no log ID is provided", async () => {
    const { result } = renderHook(() => useCancelDraftLog(undefined, 456), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe("No draft log to cancel");
  });

  it("should handle errors when delete fails", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      text: () => Promise.resolve("Log not found"),
    });

    const { result } = renderHook(() => useCancelDraftLog(123, 456), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

