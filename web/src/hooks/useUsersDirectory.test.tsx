import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useUsersDirectory } from "./useUsersDirectory";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const baseResponse = {
  items: [
    {
      id: 1,
      name: "alice",
      member_since: "2024-01-01",
      stats: { total_logs: 1, total_trigs_logged: 1, total_photos: 0 },
      profile_path: "/profile/1",
    },
  ],
  next_cursor: null,
  total: 1,
  applied_filters: { sort: "trigs", direction: "desc", limit: 40 },
};

describe("useUsersDirectory", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockResolvedValue({
      ok: true,
      json: async () => baseResponse,
    } as Response);
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("requests the first page with default parameters", async () => {
    const { result } = renderHook(() => useUsersDirectory(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/v1/users/browse?limit=40&sort=trigs&direction=desc",
      expect.objectContaining({ method: "GET" })
    );
    expect(result.current.data?.pages[0].items[0].name).toBe("alice");
  });

  it("passes query filters and cursor values", async () => {
    const firstPage = {
      ...baseResponse,
      next_cursor: "cursor-token",
    };
    const secondPage = {
      ...baseResponse,
      items: [
        {
          ...baseResponse.items[0],
          id: 2,
          name: "bob",
          profile_path: "/profile/2",
        },
      ],
      next_cursor: null,
    };

    fetchSpy
      .mockResolvedValueOnce({
        ok: true,
        json: async () => firstPage,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => secondPage,
      } as Response);

    const { result } = renderHook(
      () => useUsersDirectory({ query: "ann" }),
      {
        wrapper: createWrapper(),
      }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    await act(async () => {
      await result.current.fetchNextPage();
    });

    expect(fetchSpy).toHaveBeenLastCalledWith(
      "http://localhost:8000/v1/users/browse?limit=40&sort=trigs&direction=desc&q=ann&cursor=cursor-token",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("requests alternative sort options", async () => {
    const { result } = renderHook(
      () => useUsersDirectory({ sort: "logs", direction: "asc" }),
      {
        wrapper: createWrapper(),
      }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/v1/users/browse?limit=40&sort=logs&direction=asc",
      expect.objectContaining({ method: "GET" })
    );
  });
});


