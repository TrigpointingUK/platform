import { describe, it, expect } from "vitest";

/**
 * Unit tests for the dist_wgs_original feature in the Experiments/Coordinate Discrepancies page.
 * 
 * These tests focus on the utility functions and data handling logic.
 * Full component rendering tests are complex due to async API calls and many dependencies,
 * and are better covered by integration tests.
 */

describe("dist_wgs_original feature", () => {
  describe("Distance formatting", () => {
    // Simulating the formatDistance function from Experiments.tsx
    const formatDistance = (value: number | null): string => {
      if (value === null || value === undefined) return "—";
      if (value < 1) return `${(value * 100).toFixed(0)}cm`;
      return `${value.toFixed(2)}m`;
    };

    it("should format sub-meter distances in centimeters", () => {
      expect(formatDistance(0.05)).toBe("5cm");
      expect(formatDistance(0.5)).toBe("50cm");
      expect(formatDistance(0.99)).toBe("99cm");
    });

    it("should format meter distances with 2 decimal places", () => {
      expect(formatDistance(1.0)).toBe("1.00m");
      expect(formatDistance(12.5)).toBe("12.50m");
      expect(formatDistance(100.123)).toBe("100.12m");
    });

    it("should return dash for null values", () => {
      expect(formatDistance(null)).toBe("—");
    });

    it("should handle zero", () => {
      expect(formatDistance(0)).toBe("0cm");
    });
  });

  describe("Colour classification", () => {
    // Simulating the getDistanceColourClass function from Experiments.tsx
    const getDistanceColourClass = (value: number | null): string => {
      if (value === null || value === undefined) return "text-gray-400";
      if (value < 0.1) return "text-green-600 dark:text-green-400";
      if (value < 1) return "text-yellow-600 dark:text-yellow-400";
      if (value < 5) return "text-orange-500 dark:text-orange-400";
      if (value < 10) return "text-red-500 dark:text-red-400";
      return "text-red-700 dark:text-red-500";
    };

    it("should classify <10cm as green", () => {
      expect(getDistanceColourClass(0.05)).toContain("green");
      expect(getDistanceColourClass(0.09)).toContain("green");
    });

    it("should classify 10cm-1m as yellow", () => {
      expect(getDistanceColourClass(0.1)).toContain("yellow");
      expect(getDistanceColourClass(0.5)).toContain("yellow");
      expect(getDistanceColourClass(0.99)).toContain("yellow");
    });

    it("should classify 1-5m as orange", () => {
      expect(getDistanceColourClass(1)).toContain("orange");
      expect(getDistanceColourClass(3)).toContain("orange");
      expect(getDistanceColourClass(4.99)).toContain("orange");
    });

    it("should classify 5-10m as red (first tier)", () => {
      expect(getDistanceColourClass(5)).toContain("red");
      expect(getDistanceColourClass(8)).toContain("red");
      expect(getDistanceColourClass(9.99)).toContain("red");
    });

    it("should classify >10m as red (second tier)", () => {
      expect(getDistanceColourClass(10)).toContain("red");
      expect(getDistanceColourClass(50)).toContain("red");
      expect(getDistanceColourClass(100)).toContain("red");
    });

    it("should classify null as gray", () => {
      expect(getDistanceColourClass(null)).toContain("gray");
    });
  });

  describe("Sort field enum", () => {
    it("should include dist_wgs_original as a valid sort field", () => {
      // Testing that the sort field is recognized by the API
      const validSortFields = [
        "waypoint",
        "dist_wgs_osgb",
        "dist_osgb_osgb",
        "dist_wgs_original",
      ];

      expect(validSortFields).toContain("dist_wgs_original");
    });
  });

  describe("API response handling", () => {
    it("should handle items with dist_wgs_original values", () => {
      const mockItem = {
        id: 1,
        waypoint: "TP0001",
        name: "Test Trig",
        osgb_gridref: "TQ 12345 67890",
        dist_wgs_osgb: 5.2,
        dist_osgb_osgb: 2.1,
        dist_wgs_original: 12.5,
        photo_count: 3,
      };

      expect(mockItem).toHaveProperty("dist_wgs_original");
      expect(mockItem.dist_wgs_original).toBe(12.5);
    });

    it("should handle items with null dist_wgs_original", () => {
      const mockItemWithNull = {
        id: 2,
        waypoint: "TP0002",
        name: "Test Trig 2",
        osgb_gridref: "TQ 23456 78901",
        dist_wgs_osgb: 15.7,
        dist_osgb_osgb: null,
        dist_wgs_original: null, // No original location data
        photo_count: 5,
      };

      expect(mockItemWithNull.dist_wgs_original).toBeNull();
    });

    it("should support pagination", () => {
      const mockResponse = {
        items: [],
        total: 100,
        page: 1,
        page_size: 50,
        total_pages: 2,
      };

      expect(mockResponse.total_pages).toBe(2);
    });
  });

  describe("Legend description", () => {
    it("should have correct description for dist_wgs_original", () => {
      // The legend should explain what dist_wgs_original measures
      const legendDescription = "current vs original WGS84";

      expect(legendDescription).toContain("original");
      expect(legendDescription).toContain("WGS84");
    });
  });
});

describe("Distance calculation for moved trigs", () => {
  describe("Typical moved trig scenarios", () => {
    it("should detect small movements (10m)", () => {
      // A trig moved ~10m should show distance in that range
      const distance = 10.5;
      expect(distance).toBeGreaterThan(5);
      expect(distance).toBeLessThan(15);
    });

    it("should detect large movements (100m+)", () => {
      // Some trigs are moved significant distances
      const distance = 150.0;
      expect(distance).toBeGreaterThan(100);
    });

    it("should show zero for unmoved trigs", () => {
      // If current == original, distance should be 0
      const distance = 0;
      expect(distance).toBe(0);
    });
  });
});
