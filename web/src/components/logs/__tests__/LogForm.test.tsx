import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import LogForm from "../LogForm";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "../../../contexts/ThemeProvider";

// Mock the hooks
vi.mock("../../../hooks/useLogPhotos", () => ({
  useLogPhotos: () => ({ data: [], isLoading: false }),
}));

// Mock PhotoManager to avoid complex setup
vi.mock("../../photos/PhotoManager", () => ({
  default: ({ logId, isEditing }: { logId: number; isEditing: boolean }) => (
    <div data-testid="photo-manager" data-log-id={logId} data-is-editing={isEditing}>
      PhotoManager Mock
    </div>
  ),
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
    
    // Click clear button - now shortened to just "Clear"
    const clearButton = screen.getByText(/Clear$/i);
    fireEvent.click(clearButton);
    
    await waitFor(() => {
      expect(locationInput.value).toBe("");
    });
  });
});

describe("LogForm - Title and Structure", () => {
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
  });

  it("should show title by default for new logs", () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    expect(screen.getByText("Log This Trig")).toBeInTheDocument();
  });

  it("should show 'Edit Log' title when existingLog is provided", () => {
    const existingLog = {
      id: 123,
      trig_id: 456,
      user_id: 1,
      date: "2024-06-15",
      time: "14:30:00",
      condition: "G",
      comment: "Test log",
      score: 8,
      osgb_eastings: 513700,
      osgb_northings: 205500,
      osgb_gridref: "TL 137 055",
      fb_number: "",
      source: "W",
      status: "P",
    };

    render(<LogForm {...defaultProps} existingLog={existingLog} />, { wrapper: createWrapper() });
    
    expect(screen.getByText("Edit Log")).toBeInTheDocument();
  });

  it("should hide title when hideTitle prop is true", () => {
    render(<LogForm {...defaultProps} hideTitle />, { wrapper: createWrapper() });
    
    expect(screen.queryByText("Log This Trig")).not.toBeInTheDocument();
    expect(screen.queryByText("Edit Log")).not.toBeInTheDocument();
  });

  it("should render three distinct sections", () => {
    render(<LogForm {...defaultProps} draftLogId={123} />, { wrapper: createWrapper() });
    
    // Check for Visit Details section header
    expect(screen.getByText("Visit Details")).toBeInTheDocument();
    
    // Check for form elements in the details section (use getAllByText for labels that may appear multiple times)
    expect(screen.getAllByText(/Date/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Condition/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Score/i).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/Comment/i)).toBeInTheDocument();
    
    // Check for action buttons
    expect(screen.getByText("Create Log")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("should show PhotoManager when draftLogId is provided", () => {
    render(<LogForm {...defaultProps} draftLogId={123} />, { wrapper: createWrapper() });
    
    const photoManager = screen.getByTestId("photo-manager");
    expect(photoManager).toBeInTheDocument();
    expect(photoManager).toHaveAttribute("data-log-id", "123");
    expect(photoManager).toHaveAttribute("data-is-editing", "true");
  });

  it("should show PhotoManager when existingLog is provided", () => {
    const existingLog = {
      id: 456,
      trig_id: 789,
      user_id: 1,
      date: "2024-06-15",
      time: "14:30:00",
      condition: "G",
      comment: "Test log",
      score: 8,
      osgb_eastings: 513700,
      osgb_northings: 205500,
      osgb_gridref: "TL 137 055",
      fb_number: "",
      source: "W",
      status: "P",
    };

    render(<LogForm {...defaultProps} existingLog={existingLog} />, { wrapper: createWrapper() });
    
    const photoManager = screen.getByTestId("photo-manager");
    expect(photoManager).toBeInTheDocument();
    expect(photoManager).toHaveAttribute("data-log-id", "456");
  });

  it("should show note about photos when no draftLogId or existingLog", () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    expect(screen.getByText(/Save your log first/i)).toBeInTheDocument();
  });

  it("should show Update Log button when editing existing log", () => {
    const existingLog = {
      id: 123,
      trig_id: 456,
      user_id: 1,
      date: "2024-06-15",
      time: "14:30:00",
      condition: "G",
      comment: "Test log",
      score: 8,
      osgb_eastings: 513700,
      osgb_northings: 205500,
      osgb_gridref: "TL 137 055",
      fb_number: "",
      source: "W",
      status: "P",
    };

    render(<LogForm {...defaultProps} existingLog={existingLog} />, { wrapper: createWrapper() });
    
    expect(screen.getByText("Update Log")).toBeInTheDocument();
  });

  it("should show Create Log button for new logs", () => {
    render(<LogForm {...defaultProps} />, { wrapper: createWrapper() });
    
    expect(screen.getByText("Create Log")).toBeInTheDocument();
  });
});
