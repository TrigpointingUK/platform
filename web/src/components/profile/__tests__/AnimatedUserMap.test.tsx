import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AnimatedUserMap from "../AnimatedUserMap";
import { ThemeProvider } from "../../../contexts/ThemeProvider";
import type { ReactNode } from "react";

// Mock the useUserLogTimeline hook
vi.mock("../../../hooks/useUserLogTimeline", () => ({
  useUserLogTimeline: vi.fn(),
}));

import { useUserLogTimeline } from "../../../hooks/useUserLogTimeline";

const mockUseUserLogTimeline = useUserLogTimeline as ReturnType<typeof vi.fn>;

// Mock canvas context
const mockCanvasContext = {
  clearRect: vi.fn(),
  drawImage: vi.fn(),
  beginPath: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  fillRect: vi.fn(),
  closePath: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  fillStyle: "",
  globalAlpha: 1,
  globalCompositeOperation: "source-over",
};

// Mock HTMLCanvasElement.getContext
HTMLCanvasElement.prototype.getContext = vi.fn(() => mockCanvasContext) as unknown as typeof HTMLCanvasElement.prototype.getContext;

// Mock Image
class MockImage {
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  src = "";
  width = 1200;
  height = 1196;

  constructor() {
    // Simulate image load after a short delay
    setTimeout(() => {
      if (this.onload) this.onload();
    }, 10);
  }
}

// Replace global Image with mock
vi.stubGlobal("Image", MockImage);

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
};

const mockTimeline = [
  { lat: 51.5072, lon: -0.1276, date: "2020-01-15", colour: "green" as const },
  { lat: 55.9533, lon: -3.1883, date: "2020-03-22", colour: "yellow" as const },
  { lat: 53.4808, lon: -2.2426, date: "2020-06-10", colour: "green" as const },
  { lat: 50.0659, lon: -5.7139, date: "2021-01-05", colour: "red" as const },
  { lat: 54.9783, lon: -1.6178, date: "2021-06-15", colour: "grey" as const },
];

describe("AnimatedUserMap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  describe("loading states", () => {
    it("should show spinner while loading", () => {
      mockUseUserLogTimeline.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<AnimatedUserMap userId={123} />, { wrapper: createWrapper() });

      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should show error message when fetch fails", () => {
      mockUseUserLogTimeline.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Failed to fetch"),
      });

      render(<AnimatedUserMap userId={123} />, { wrapper: createWrapper() });

      expect(screen.getByText("Failed to load timeline")).toBeInTheDocument();
    });

    it("should show empty state when no logs", () => {
      mockUseUserLogTimeline.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      render(<AnimatedUserMap userId={123} />, { wrapper: createWrapper() });

      expect(screen.getByText("No logs to display")).toBeInTheDocument();
    });
  });

  describe("rendering with data", () => {
    beforeEach(() => {
      mockUseUserLogTimeline.mockReturnValue({
        data: mockTimeline,
        isLoading: false,
        error: null,
      });
    });

    it("should render canvas element", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(document.querySelector("canvas")).toBeInTheDocument();
      });
    });

    it("should render play button", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Play")).toBeInTheDocument();
      });
    });

    it("should render speed selector buttons", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText("0.1x")).toBeInTheDocument();
        expect(screen.getByText("1x")).toBeInTheDocument();
        expect(screen.getByText("10x")).toBeInTheDocument();
      });
    });

    it("should render skip navigation buttons", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Skip to start")).toBeInTheDocument();
        expect(screen.getByLabelText("Skip back one year")).toBeInTheDocument();
        expect(screen.getByLabelText("Skip back one month")).toBeInTheDocument();
        expect(screen.getByLabelText("Skip forward one month")).toBeInTheDocument();
        expect(screen.getByLabelText("Skip forward one year")).toBeInTheDocument();
        expect(screen.getByLabelText("Skip to end")).toBeInTheDocument();
      });
    });

    it("should render sound toggle button", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Unmute")).toBeInTheDocument();
      });
    });

    it("should render log count stats", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        // Should show "0 / 5 logs" initially
        expect(screen.getByText("/ 5 logs")).toBeInTheDocument();
      });
    });

    it("should render date range labels", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText("2020-01-15")).toBeInTheDocument();
        expect(screen.getByText("2021-06-15")).toBeInTheDocument();
      });
    });
  });

  describe("playback controls", () => {
    beforeEach(() => {
      mockUseUserLogTimeline.mockReturnValue({
        data: mockTimeline,
        isLoading: false,
        error: null,
      });
    });

    it("should toggle play/pause when play button clicked", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Play")).toBeInTheDocument();
      });

      const playButton = screen.getByLabelText("Play");
      fireEvent.click(playButton);

      await waitFor(() => {
        expect(screen.getByLabelText("Pause")).toBeInTheDocument();
      });
    });

    it("should change speed when speed button clicked", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText("10x")).toBeInTheDocument();
      });

      const speedButton = screen.getByText("10x");
      fireEvent.click(speedButton);

      // The 10x button should now be highlighted (has the green background)
      expect(speedButton).toHaveClass("bg-trig-green-600");
    });

    it("should toggle sound when sound button clicked", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Unmute")).toBeInTheDocument();
      });

      const soundButton = screen.getByLabelText("Unmute");
      fireEvent.click(soundButton);

      await waitFor(() => {
        expect(screen.getByLabelText("Mute")).toBeInTheDocument();
      });
    });
  });

  describe("skip navigation", () => {
    beforeEach(() => {
      mockUseUserLogTimeline.mockReturnValue({
        data: mockTimeline,
        isLoading: false,
        error: null,
      });
    });

    it("should skip to end when skip to end button clicked", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Skip to end")).toBeInTheDocument();
      });

      const skipEndButton = screen.getByLabelText("Skip to end");
      fireEvent.click(skipEndButton);

      // After skipping to end, the displayed count should be all logs
      await waitFor(() => {
        expect(screen.getByText("5")).toBeInTheDocument();
      });
    });

    it("should reset when skip to start button clicked after playing", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Skip to end")).toBeInTheDocument();
      });

      // First skip to end
      fireEvent.click(screen.getByLabelText("Skip to end"));

      await waitFor(() => {
        expect(screen.getByText("5")).toBeInTheDocument();
      });

      // Then skip to start
      fireEvent.click(screen.getByLabelText("Skip to start"));

      await waitFor(() => {
        expect(screen.getByText("0")).toBeInTheDocument();
      });
    });
  });

  describe("props", () => {
    beforeEach(() => {
      mockUseUserLogTimeline.mockReturnValue({
        data: mockTimeline,
        isLoading: false,
        error: null,
      });
    });

    it("should accept numeric userId", () => {
      render(<AnimatedUserMap userId={123} />, { wrapper: createWrapper() });

      expect(mockUseUserLogTimeline).toHaveBeenCalledWith(123);
    });

    it("should accept string userId", () => {
      render(<AnimatedUserMap userId="456" />, { wrapper: createWrapper() });

      expect(mockUseUserLogTimeline).toHaveBeenCalledWith("456");
    });

    it("should apply custom height", async () => {
      render(<AnimatedUserMap userId={123} height={500} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        const canvas = document.querySelector("canvas");
        expect(canvas).toHaveAttribute("height", "500");
      });
    });

    it("should not autoplay when autoPlay is false", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Play")).toBeInTheDocument();
      });

      // Should still show Play button (not Pause) after component mounts
      expect(screen.getByLabelText("Play")).toBeInTheDocument();
    });
  });

  describe("date display format", () => {
    beforeEach(() => {
      mockUseUserLogTimeline.mockReturnValue({
        data: mockTimeline,
        isLoading: false,
        error: null,
      });
    });

    it("should display date in 'Mon YYYY' format after skipping", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByLabelText("Skip to end")).toBeInTheDocument();
      });

      // Skip to end to display a date
      fireEvent.click(screen.getByLabelText("Skip to end"));

      // The date overlay should show month name format (e.g., "Jun 2021")
      await waitFor(() => {
        // Look for the year/month overlay which should contain a month abbreviation
        const overlay = screen.getByText(/Jun 2021/);
        expect(overlay).toBeInTheDocument();
      });
    });
  });

  describe("progress bar", () => {
    beforeEach(() => {
      mockUseUserLogTimeline.mockReturnValue({
        data: mockTimeline,
        isLoading: false,
        error: null,
      });
    });

    it("should render progress bar", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        // Progress bar container
        const progressBar = document.querySelector(".h-2.bg-gray-200");
        expect(progressBar).toBeInTheDocument();
      });
    });

    it("should update progress when scrubbing", async () => {
      render(<AnimatedUserMap userId={123} autoPlay={false} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(document.querySelector("canvas")).toBeInTheDocument();
      });

      const scrubber = document.querySelector(".h-2.bg-gray-200");
      expect(scrubber).toBeInTheDocument();

      if (scrubber) {
        // Simulate click on scrubber at 50% position
        const rect = { left: 0, width: 100 };
        Object.defineProperty(scrubber, "getBoundingClientRect", {
          value: () => rect,
        });

        fireEvent.click(scrubber, { clientX: 50 });

        // Should have advanced the timeline
        await waitFor(() => {
          const progressFill = scrubber.querySelector(".bg-trig-green-600");
          expect(progressFill).toBeInTheDocument();
        });
      }
    });
  });
});

