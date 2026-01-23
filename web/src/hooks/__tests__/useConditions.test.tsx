import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useConditions, buildConditionMap, getConditionFromMap } from "../useConditions";
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
    wiki_url: "https://wiki.example.com/Good",
    sort_order: 1,
  },
  {
    code: "S",
    name: "Slightly Damaged",
    description: "Minor damage",
    icon_file: "c_slightlydamaged.png",
    trig_colour: "green",
    log_colour: "green",
    similar_codes: "GD",
    wiki_url: null,
    sort_order: 2,
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

describe("useConditions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch conditions successfully", async () => {
    vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

    const { result } = renderHook(() => useConditions(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockConditions);
    expect(result.current.data).toHaveLength(4);
  });

  it("should call the API", async () => {
    // Simple test to verify the API is called - error handling is react-query's responsibility
    vi.mocked(fetchPublicConditions).mockResolvedValue(mockConditions);

    renderHook(() => useConditions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(fetchPublicConditions).toHaveBeenCalled();
    });
  });

  it("should return empty array when API returns empty", async () => {
    vi.mocked(fetchPublicConditions).mockResolvedValue([]);

    const { result } = renderHook(() => useConditions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });
});

describe("buildConditionMap", () => {
  it("should build a map from conditions array", () => {
    const map = buildConditionMap(mockConditions);

    expect(map.size).toBe(4);
    expect(map.get("G")).toEqual(mockConditions[0]);
    expect(map.get("S")).toEqual(mockConditions[1]);
    expect(map.get("D")).toEqual(mockConditions[2]);
    expect(map.get("X")).toEqual(mockConditions[3]);
  });

  it("should handle empty array", () => {
    const map = buildConditionMap([]);

    expect(map.size).toBe(0);
  });

  it("should use code as key", () => {
    const map = buildConditionMap(mockConditions);

    // Verify keys are the codes
    expect(Array.from(map.keys())).toEqual(["G", "S", "D", "X"]);
  });
});

describe("getConditionFromMap", () => {
  const conditionMap = buildConditionMap(mockConditions);

  it("should return condition for valid code", () => {
    const condition = getConditionFromMap(conditionMap, "G");

    expect(condition).toEqual(mockConditions[0]);
    expect(condition?.name).toBe("Good");
  });

  it("should handle lowercase code", () => {
    const condition = getConditionFromMap(conditionMap, "g");

    expect(condition).toEqual(mockConditions[0]);
  });

  it("should return undefined for unknown code", () => {
    const condition = getConditionFromMap(conditionMap, "Z");

    expect(condition).toBeUndefined();
  });

  it("should return undefined for null code", () => {
    const condition = getConditionFromMap(conditionMap, null);

    expect(condition).toBeUndefined();
  });

  it("should return undefined for undefined code", () => {
    const condition = getConditionFromMap(conditionMap, undefined);

    expect(condition).toBeUndefined();
  });

  it("should return undefined for empty string code", () => {
    const condition = getConditionFromMap(conditionMap, "");

    expect(condition).toBeUndefined();
  });
});

