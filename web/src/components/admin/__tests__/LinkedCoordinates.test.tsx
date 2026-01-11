import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import "@testing-library/jest-dom";
import LinkedCoordinates from "../LinkedCoordinates";

// Mock the API module
vi.mock("../../../lib/api", () => ({
  convertCoordinates: vi.fn(),
}));

// Import the mocked function for test assertions
import { convertCoordinates, CoordinateConversionResponse } from "../../../lib/api";
const mockConvertCoordinates = vi.mocked(convertCoordinates);

describe("LinkedCoordinates", () => {
  const defaultProps = {
    wgsLat: "51.50740",
    wgsLong: "-0.12760",
    wgsHeight: 100,
    osgbEastings: 530034,
    osgbNorthings: 179382,
    osgbGridref: "TQ 30034 79382",
    osgbHeight: 55,
    onWgsChange: vi.fn(),
    onOsgbChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Initial Rendering", () => {
    it("renders all WGS84 input fields with initial values", () => {
      render(<LinkedCoordinates {...defaultProps} />);

      const latInput = screen.getByPlaceholderText("e.g., 52.12345") as HTMLInputElement;
      const lonInput = screen.getByPlaceholderText("e.g., -2.12345") as HTMLInputElement;

      expect(latInput.value).toBe("51.50740");
      expect(lonInput.value).toBe("-0.12760");
    });

    it("renders all OSGB input fields with initial values", () => {
      render(<LinkedCoordinates {...defaultProps} />);

      const eastingsInput = screen.getByPlaceholderText("e.g., 512345") as HTMLInputElement;
      const northingsInput = screen.getByPlaceholderText("e.g., 212345") as HTMLInputElement;
      const gridrefInput = screen.getByPlaceholderText("e.g., SO 12345 67890") as HTMLInputElement;

      expect(eastingsInput.value).toBe("530034");
      expect(northingsInput.value).toBe("179382");
      expect(gridrefInput.value).toBe("TQ 30034 79382");
    });

    it("renders height fields with initial values", () => {
      render(<LinkedCoordinates {...defaultProps} />);

      const wgsHeightInput = screen.getAllByRole("spinbutton")[0] as HTMLInputElement;
      const osgbHeightInput = screen.getAllByRole("spinbutton")[1] as HTMLInputElement;

      expect(wgsHeightInput.value).toBe("100");
      expect(osgbHeightInput.value).toBe("55");
    });

    it("renders grid reference field as readonly", () => {
      render(<LinkedCoordinates {...defaultProps} />);

      const gridrefInput = screen.getByPlaceholderText("e.g., SO 12345 67890");
      expect(gridrefInput).toHaveAttribute("readonly");
    });

    it("renders section headers", () => {
      render(<LinkedCoordinates {...defaultProps} />);

      expect(screen.getByText("WGS84 Coordinates")).toBeInTheDocument();
      expect(screen.getByText("OSGB36 Coordinates")).toBeInTheDocument();
    });
  });

  describe("WGS84 to OSGB Conversion", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("triggers API call after debounce when latitude changes", async () => {
      mockConvertCoordinates.mockResolvedValue({
        from_crs: "wgs84",
        to_crs: "osgb",
        input: { lat: 52.0, lon: -0.1276, height: 100 },
        output: { e: 450000, n: 250000, height: 55, gridref: "SP 50000 50000" },
      });

      render(<LinkedCoordinates {...defaultProps} />);

      const latInput = screen.getByPlaceholderText("e.g., 52.12345");
      fireEvent.focus(latInput);
      fireEvent.change(latInput, { target: { value: "52.00000" } });

      // API should not be called immediately
      expect(mockConvertCoordinates).not.toHaveBeenCalled();

      // Run all timers and wait for promises
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(mockConvertCoordinates).toHaveBeenCalledWith({
        from: "wgs84",
        to: "osgb",
        lat: 52.0,
        lon: -0.1276,
        height: 100,
      });
    });

    it("updates OSGB fields after successful conversion", async () => {
      const onOsgbChange = vi.fn();
      mockConvertCoordinates.mockResolvedValue({
        from_crs: "wgs84",
        to_crs: "osgb",
        input: { lat: 52.0, lon: -1.0, height: 100 },
        output: { e: 450000, n: 250000, height: 55, gridref: "SP 50000 50000" },
      });

      render(<LinkedCoordinates {...defaultProps} onOsgbChange={onOsgbChange} />);

      const latInput = screen.getByPlaceholderText("e.g., 52.12345");
      fireEvent.focus(latInput);
      fireEvent.change(latInput, { target: { value: "52.00000" } });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(onOsgbChange).toHaveBeenCalledWith(450000, 250000, "SP 50000 50000", 55);
    });
  });

  describe("OSGB to WGS84 Conversion", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("triggers API call after debounce when eastings changes", async () => {
      mockConvertCoordinates.mockResolvedValue({
        from_crs: "osgb",
        to_crs: "wgs84",
        input: { e: 400000, n: 179382, height: 55, gridref: "SU 00000 79382" },
        output: { lat: 51.5, lon: -1.0, height: 100 },
      });

      render(<LinkedCoordinates {...defaultProps} />);

      const eastingsInput = screen.getByPlaceholderText("e.g., 512345");
      fireEvent.focus(eastingsInput);
      fireEvent.change(eastingsInput, { target: { value: "400000" } });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(mockConvertCoordinates).toHaveBeenCalledWith({
        from: "osgb",
        to: "wgs84",
        e: 400000,
        n: 179382,
        height: 55,
      });
    });

    it("updates WGS84 fields after successful conversion", async () => {
      const onWgsChange = vi.fn();
      mockConvertCoordinates.mockResolvedValue({
        from_crs: "osgb",
        to_crs: "wgs84",
        input: { e: 400000, n: 300000, height: 60, gridref: "SU 00000 00000" },
        output: { lat: 52.12345, lon: -1.54321, height: 105 },
      });

      render(<LinkedCoordinates {...defaultProps} onWgsChange={onWgsChange} />);

      const eastingsInput = screen.getByPlaceholderText("e.g., 512345");
      fireEvent.focus(eastingsInput);
      fireEvent.change(eastingsInput, { target: { value: "400000" } });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(onWgsChange).toHaveBeenCalledWith("52.12345", "-1.54321", 105);
    });
  });

  describe("Height Conversion", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("includes height in WGS84 to OSGB conversion", async () => {
      mockConvertCoordinates.mockResolvedValue({
        from_crs: "wgs84",
        to_crs: "osgb",
        input: { lat: 51.5074, lon: -0.1276, height: 150 },
        output: { e: 530034, n: 179382, height: 105, gridref: "TQ 30034 79382" },
      });

      render(<LinkedCoordinates {...defaultProps} />);

      const heightInputs = screen.getAllByRole("spinbutton");
      const wgsHeightInput = heightInputs[0];
      fireEvent.focus(wgsHeightInput);
      fireEvent.change(wgsHeightInput, { target: { value: "150" } });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(mockConvertCoordinates).toHaveBeenCalledWith({
        from: "wgs84",
        to: "osgb",
        lat: 51.5074,
        lon: -0.1276,
        height: 150,
      });
    });

    it("includes height in OSGB to WGS84 conversion", async () => {
      mockConvertCoordinates.mockResolvedValue({
        from_crs: "osgb",
        to_crs: "wgs84",
        input: { e: 530034, n: 179382, height: 80, gridref: "TQ 30034 79382" },
        output: { lat: 51.5074, lon: -0.1276, height: 125 },
      });

      render(<LinkedCoordinates {...defaultProps} />);

      const heightInputs = screen.getAllByRole("spinbutton");
      const osgbHeightInput = heightInputs[1];
      fireEvent.focus(osgbHeightInput);
      fireEvent.change(osgbHeightInput, { target: { value: "80" } });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(mockConvertCoordinates).toHaveBeenCalledWith({
        from: "osgb",
        to: "wgs84",
        e: 530034,
        n: 179382,
        height: 80,
      });
    });
  });

  describe("Error Handling", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("shows error message when conversion fails", async () => {
      mockConvertCoordinates.mockRejectedValue(new Error("Conversion failed: Invalid coordinates"));

      render(<LinkedCoordinates {...defaultProps} />);

      const latInput = screen.getByPlaceholderText("e.g., 52.12345");
      fireEvent.focus(latInput);
      fireEvent.change(latInput, { target: { value: "91.00000" } });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText(/conversion failed/i)).toBeInTheDocument();
    });
  });

  describe("Debounce Behavior", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("does not call API when input is invalid (NaN)", async () => {
      render(<LinkedCoordinates {...defaultProps} />);

      const latInput = screen.getByPlaceholderText("e.g., 52.12345");
      fireEvent.focus(latInput);
      fireEvent.change(latInput, { target: { value: "not a number" } });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // API should not be called for invalid input
      expect(mockConvertCoordinates).not.toHaveBeenCalled();
    });

    it("debounces rapid changes and only calls API once with final value", async () => {
      mockConvertCoordinates.mockResolvedValue({
        from_crs: "wgs84",
        to_crs: "osgb",
        input: { lat: 52.5, lon: -0.1276, height: 100 },
        output: { e: 450000, n: 250000, height: 55, gridref: "SP 50000 50000" },
      });

      render(<LinkedCoordinates {...defaultProps} />);

      const latInput = screen.getByPlaceholderText("e.g., 52.12345");
      fireEvent.focus(latInput);

      // Type several values rapidly
      fireEvent.change(latInput, { target: { value: "52.1" } });
      await act(async () => {
        vi.advanceTimersByTime(100);
      });

      fireEvent.change(latInput, { target: { value: "52.3" } });
      await act(async () => {
        vi.advanceTimersByTime(100);
      });

      fireEvent.change(latInput, { target: { value: "52.5" } });

      // Now let all timers complete
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // Should only have been called once with the final value
      expect(mockConvertCoordinates).toHaveBeenCalledTimes(1);
      expect(mockConvertCoordinates).toHaveBeenCalledWith({
        from: "wgs84",
        to: "osgb",
        lat: 52.5,
        lon: -0.1276,
        height: 100,
      });
    });
  });

  describe("UI Behavior", () => {
    it("inputs are never disabled - allows continuous typing during conversion", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });

      // Use a pending promise to simulate slow API
      let resolvePromise!: (value: CoordinateConversionResponse) => void;
      mockConvertCoordinates.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      render(<LinkedCoordinates {...defaultProps} />);

      const latInput = screen.getByPlaceholderText("e.g., 52.12345");
      const lonInput = screen.getByPlaceholderText("e.g., -2.12345");

      // Focus and change latitude
      fireEvent.focus(latInput);
      fireEvent.change(latInput, { target: { value: "52.00000" } });

      // Advance past debounce
      await act(async () => {
        vi.advanceTimersByTime(500);
      });

      // Even during API call, inputs should NOT be disabled
      expect(latInput).not.toBeDisabled();
      expect(lonInput).not.toBeDisabled();

      // Resolve the API call
      await act(async () => {
        resolvePromise!({
          from_crs: "wgs84",
          to_crs: "osgb",
          input: { lat: 52.0, lon: -0.1276, height: 100 },
          output: { e: 450000, n: 250000, height: 55, gridref: "SP 50000 50000" },
        });
        await vi.runAllTimersAsync();
      });

      // Still not disabled after completion
      expect(latInput).not.toBeDisabled();
      expect(lonInput).not.toBeDisabled();

      vi.useRealTimers();
    });
  });
});
