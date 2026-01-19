import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import LogForm from "../LogForm";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "../../../contexts/ThemeContext";

// Mock the hooks
vi.mock("../../hooks/useLogPhotos", () => ({
  useLogPhotos: () => ({ data: [] }),
}));

// Mock the API module to avoid network calls
vi.mock("../../../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../lib/api")>();
  return {
    ...actual,
    convertCoordinates: vi.fn().mockResolvedValue({
      from_crs: "osgb",
      to_crs: "wgs84",
      input: { e: 513700, n: 205500, gridref: "TL 13700 05500" },
      output: { lat: 51.736691, lon: -0.354803 },
      grid_system: "gb",
    }),
  };
});

// Import the mocked function for manipulation in tests
import { convertCoordinates } from "../../../lib/api";

// Create a wrapper with QueryClient and ThemeProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ThemeProvider>
  );
};

describe("LogForm - Location Input", () => {
  const defaultProps = {
    trigGridRef: "TL 137 055",
    trigEastings: 513700,
    trigNorthings: 205500,
    trigLatitude: 52.0,
    trigLongitude: -1.0,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    isSubmitting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock returns coordinates near the trig point
    vi.mocked(convertCoordinates).mockResolvedValue({
      from_crs: "osgb",
      to_crs: "wgs84",
      input: { e: 513700, n: 205500, gridref: "TL 13700 05500" },
      output: { lat: 52.0001, lon: -1.0001 },
      grid_system: "gb",
    });
  });

  it("should render editable location input", () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i);
    expect(locationInput).toBeInTheDocument();
    expect(locationInput).not.toHaveAttribute("readonly");
  });

  it("should auto-uppercase location input", () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i) as HTMLInputElement;
    
    fireEvent.change(locationInput, { target: { value: "tl137055" } });
    
    expect(locationInput.value).toBe("TL137055");
  });

  it("should parse valid grid reference and show distance", async () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i);
    const distanceInput = screen.getByPlaceholderText(/Distance/i) as HTMLInputElement;
    
    fireEvent.change(locationInput, { target: { value: "TL 137 055" } });
    
    await waitFor(() => {
      // Distance should be calculated (very close to trig location)
      expect(distanceInput.value).toMatch(/\d+\.\d+m from trig/);
    });
  });

  it("should show validation error for invalid grid reference", async () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i);
    
    // Enter invalid grid reference
    fireEvent.change(locationInput, { target: { value: "INVALID" } });
    
    await waitFor(() => {
      // The input should have a red border when invalid
      expect(locationInput).toHaveClass("border-red-300");
    });
  });

  it("should parse valid lat/long coordinates", async () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i);
    const distanceInput = screen.getByPlaceholderText(/Distance/i) as HTMLInputElement;
    
    fireEvent.change(locationInput, { target: { value: "52.0, -1.0" } });
    
    await waitFor(() => {
      // Distance should be calculated
      expect(distanceInput.value).toMatch(/\d+\.\d+m from trig/);
    });
  });

  it("should clear distance when input is cleared", async () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i);
    const distanceInput = screen.getByPlaceholderText(/Distance/i) as HTMLInputElement;
    
    // Enter valid location
    fireEvent.change(locationInput, { target: { value: "TL 137 055" } });
    
    await waitFor(() => {
      expect(distanceInput.value).not.toBe("");
    });
    
    // Clear input
    fireEvent.change(locationInput, { target: { value: "" } });
    
    await waitFor(() => {
      expect(distanceInput.value).toBe("");
    });
  });

  it("should show distance > 20m for far location", async () => {
    // Mock returns coordinates about 600m away from trig (52.0, -1.0)
    vi.mocked(convertCoordinates).mockResolvedValue({
      from_crs: "osgb",
      to_crs: "wgs84",
      input: { e: 514000, n: 206000, gridref: "TL 14000 06000" },
      output: { lat: 52.005, lon: -0.995 },
      grid_system: "gb",
    });
    
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i);
    
    // Enter a location far from the trig
    fireEvent.change(locationInput, { target: { value: "TL 140 060" } });
    
    await waitFor(() => {
      const distanceInput = screen.getByPlaceholderText(/Distance/i) as HTMLInputElement;
      expect(distanceInput.value).toMatch(/\d+\.\d+m from trig/);
      const distance = parseFloat(distanceInput.value);
      expect(distance).toBeGreaterThan(20);
    });
  });

  it("should calculate distance correctly", async () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i);
    
    // Enter a valid location
    fireEvent.change(locationInput, { target: { value: "TL 137 055" } });
    
    await waitFor(() => {
      const distanceInput = screen.getByPlaceholderText(/Distance/i) as HTMLInputElement;
      // Distance should be calculated and displayed
      expect(distanceInput.value).toMatch(/\d+(\.\d+)?m from trig/);
    });
  });

  it("should clear location when Clear button is clicked", async () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    const locationInput = screen.getByPlaceholderText(/Enter grid ref/i) as HTMLInputElement;
    
    // Enter valid location
    fireEvent.change(locationInput, { target: { value: "TL 137 055" } });
    
    await waitFor(() => {
      expect(locationInput.value).toBe("TL 137 055");
    });
    
    // Click clear button
    const clearButton = screen.getByText(/Clear Location/i);
    fireEvent.click(clearButton);
    
    await waitFor(() => {
      expect(locationInput.value).toBe("");
    });
  });
});
