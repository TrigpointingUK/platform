import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useUserLogTimeline, type TimelineEntry } from "../useUserLogTimeline";
import type { ReactNode } from "react";

// Create a wrapper with QueryClientProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockTimeline: TimelineEntry[] = [
  { lat: 51.5072, lon: -0.1276, date: "2020-01-15", colour: "green" },
  { lat: 55.9533, lon: -3.1883, date: "2020-03-22", colour: "yellow" },
  { lat: 53.4808, lon: -2.2426, date: "2020-06-10", colour: "green" },
  { lat: 50.0659, lon: -5.7139, date: "2021-01-05", colour: "red" },
  { lat: 54.9783, lon: -1.6178, date: null, colour: "grey" },
];

describe("useUserLogTimeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should fetch timeline data successfully", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTimeline),
    } as Response);

    const { result } = renderHook(() => useUserLogTimeline(123), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockTimeline);
    expect(result.current.data).toHaveLength(5);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/users/123/log-timeline")
    );

    mockFetch.mockRestore();
  });

  it("should handle string userId", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTimeline),
    } as Response);

    const { result } = renderHook(() => useUserLogTimeline("456"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/users/456/log-timeline")
    );

    mockFetch.mockRestore();
  });

  it("should handle API errors", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
    } as Response);

    const { result } = renderHook(() => useUserLogTimeline(999), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("Failed to fetch log timeline");

    mockFetch.mockRestore();
  });

  it("should handle empty timeline", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    } as Response);

    const { result } = renderHook(() => useUserLogTimeline(123), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.data).toHaveLength(0);

    mockFetch.mockRestore();
  });

  it("should return entries with correct structure", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTimeline),
    } as Response);

    const { result } = renderHook(() => useUserLogTimeline(123), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const firstEntry = result.current.data?.[0];
    expect(firstEntry).toHaveProperty("lat");
    expect(firstEntry).toHaveProperty("lon");
    expect(firstEntry).toHaveProperty("date");
    expect(firstEntry).toHaveProperty("colour");
    expect(typeof firstEntry?.lat).toBe("number");
    expect(typeof firstEntry?.lon).toBe("number");

    mockFetch.mockRestore();
  });

  it("should handle network errors", async () => {
    const mockFetch = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useUserLogTimeline(123), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(Error);

    mockFetch.mockRestore();
  });

  it("should have correct query key structure", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTimeline),
    } as Response);

    // Render with different user IDs to verify query keys are different
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result: result1 } = renderHook(() => useUserLogTimeline(123), {
      wrapper,
    });
    const { result: result2 } = renderHook(() => useUserLogTimeline(456), {
      wrapper,
    });

    await waitFor(() => {
      expect(result1.current.isSuccess).toBe(true);
      expect(result2.current.isSuccess).toBe(true);
    });

    // Both should have been called
    expect(mockFetch).toHaveBeenCalledTimes(2);

    mockFetch.mockRestore();
  });

  it("should handle entries with null dates", async () => {
    const timelineWithNullDate: TimelineEntry[] = [
      { lat: 51.5, lon: -0.1, date: null, colour: "grey" },
    ];

    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(timelineWithNullDate),
    } as Response);

    const { result } = renderHook(() => useUserLogTimeline(123), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.[0].date).toBeNull();

    mockFetch.mockRestore();
  });

  it("should handle all valid colour values", async () => {
    const timelineWithAllColours: TimelineEntry[] = [
      { lat: 51.0, lon: -0.1, date: "2020-01-01", colour: "green" },
      { lat: 52.0, lon: -0.2, date: "2020-02-01", colour: "yellow" },
      { lat: 53.0, lon: -0.3, date: "2020-03-01", colour: "red" },
      { lat: 54.0, lon: -0.4, date: "2020-04-01", colour: "grey" },
    ];

    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(timelineWithAllColours),
    } as Response);

    const { result } = renderHook(() => useUserLogTimeline(123), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const colours = result.current.data?.map((e) => e.colour);
    expect(colours).toContain("green");
    expect(colours).toContain("yellow");
    expect(colours).toContain("red");
    expect(colours).toContain("grey");

    mockFetch.mockRestore();
  });
});

