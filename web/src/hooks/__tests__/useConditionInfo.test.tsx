import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useConditionInfo, getConditionInfoFallback } from "../useConditionInfo";
import type { Condition } from "../../lib/api";

// Mock the API
vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    fetchPublicConditions: vi.fn(),
  };
});

import { fetchPublicConditions } from "../../lib/api";

const mockConditions: Condition[] = [
  {
    code: "G",
    name: "Good",
    description: "Trigpoint is in good condition",
    icon_file: "c_good.png",
    trig_colour: "green",
    log_colour: "green",
    similar_codes: "S",
    wiki_url: null,
    sort_order: 1,
  },
  {
    code: "D",
    name: "Damaged",
    description: "Significant damage",
    icon_file: "c_damaged.png",
    trig_colour: "yellow",
    log_colour: "yellow",
    similar_codes: "S",
    wiki_url: null,
    sort_order: 3,
  },
  {
    code: "X",
    name: "Destroyed",
    description: "Completely destroyed",
    icon_file: "c_definitelymissing.png",
    trig_colour: "red",
    log_colour: "red",
    similar_codes: null,
    wiki_url: null,
    sort_order: 10,
  },
];

// Create a wrapper with QueryClientProvider
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

describe("useConditionInfo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("with API data loaded", () => {
    it("should return condition info from API", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo("G");

      expect(info.label).toBe("Good");
      expect(info.icon).toBe("c_good.png");
      expect(info.variant).toBe("good");
    });

    it("should handle lowercase codes", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo("g");

      expect(info.label).toBe("Good");
    });

    it("should return correct variant for yellow conditions", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo("D");

      expect(info.variant).toBe("damaged");
    });

    it("should return correct variant for red conditions", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo("X");

      expect(info.variant).toBe("missing");
    });
  });

  describe("with fallback data", () => {
    it("should use fallback when API not loaded", async () => {
      // Never resolve the API call
      vi.mocked(fetchPublicConditions).mockImplementation(
        () => new Promise(() => {})
      );

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      // Should be loading
      expect(result.current.isLoading).toBe(true);

      // getConditionInfo should still work with fallback
      const info = result.current.getConditionInfo("G");

      expect(info.label).toBe("Good");
      expect(info.icon).toBe("c_good.png");
    });

    it("should use fallback for unknown codes", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo("UNKNOWN");

      expect(info.label).toBe("UNKNOWN");
      expect(info.icon).toBe("c_unknown.png");
      expect(info.variant).toBe("unknown");
    });
  });

  describe("edge cases", () => {
    it("should handle null code", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo(null);

      expect(info.label).toBe("Not Visited");
      expect(info.icon).toBe("c_nolog.png");
    });

    it("should handle undefined code", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo(undefined);

      expect(info.label).toBe("Not Visited");
    });

    it("should handle empty string code", async () => {
      vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

      const { result } = renderHook(() => useConditionInfo(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const info = result.current.getConditionInfo("");

      expect(info.label).toBe("Not Visited");
    });
  });
});

describe("getConditionInfoFallback", () => {
  it("should return info for known codes", () => {
    expect(getConditionInfoFallback("G").label).toBe("Good");
    expect(getConditionInfoFallback("D").label).toBe("Damaged");
    expect(getConditionInfoFallback("X").label).toBe("Destroyed");
    expect(getConditionInfoFallback("N").label).toBe("Couldn't Find");
  });

  it("should handle lowercase codes", () => {
    expect(getConditionInfoFallback("g").label).toBe("Good");
    expect(getConditionInfoFallback("d").label).toBe("Damaged");
  });

  it("should return unknown for unrecognised codes", () => {
    const info = getConditionInfoFallback("INVALID");

    expect(info.label).toBe("INVALID");
    expect(info.icon).toBe("c_unknown.png");
    expect(info.variant).toBe("unknown");
  });

  it("should return correct icons", () => {
    expect(getConditionInfoFallback("G").icon).toBe("c_good.png");
    expect(getConditionInfoFallback("D").icon).toBe("c_damaged.png");
    expect(getConditionInfoFallback("Q").icon).toBe("c_possiblymissing.png");
    expect(getConditionInfoFallback("X").icon).toBe("c_definitelymissing.png");
  });

  it("should return correct variants", () => {
    expect(getConditionInfoFallback("G").variant).toBe("good");
    expect(getConditionInfoFallback("S").variant).toBe("good");
    expect(getConditionInfoFallback("D").variant).toBe("damaged");
    expect(getConditionInfoFallback("X").variant).toBe("missing");
    expect(getConditionInfoFallback("P").variant).toBe("unknown");
  });
});

