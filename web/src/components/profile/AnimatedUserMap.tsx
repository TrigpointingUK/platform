/**
 * Animated user map component.
 *
 * Displays a canvas-based animated visualisation of a user's trig logging history,
 * showing dots appearing chronologically on a UK map with pulsing effects.
 */

import { useRef, useEffect, useState, useCallback, useMemo } from "react";
import {
  Play,
  Pause,
  SkipBack,
  Volume2,
  VolumeX,
  ChevronsLeft,
  ChevronsRight,
  ChevronLeft,
  ChevronRight,
  SkipForward,
} from "lucide-react";
import {
  useUserLogTimeline,
  type TimelineEntry,
} from "../../hooks/useUserLogTimeline";
import {
  latLonToScaledPixel,
  MAP_DIMENSIONS,
  getLogColourHex,
} from "../../lib/mapCalibration";
import { useTheme } from "../../hooks/useTheme";
import Spinner from "../ui/Spinner";

/** Map colour schemes for light and dark modes */
const MAP_COLOURS = {
  light: {
    sea: "#ffffff",
    land: "#d9d2ca", // 25% warm grey
    coastline: "#a0998f", // Subtle dark coastline
    coastlineWidth: 1,
  },
  dark: {
    sea: "#1f2937", // gray-800
    land: "#374151", // gray-700
    coastline: "#4b5563", // gray-600
    coastlineWidth: 0.5,
  },
};

interface AnimatedUserMapProps {
  userId: number | string;
  /** Auto-play animation on mount */
  autoPlay?: boolean;
  /** Height of the map container in pixels */
  height?: number;
}

/** Playback speed options */
const SPEED_OPTIONS = [
  { label: "0.1x", value: 0.1 },
  { label: "1x", value: 1 },
  { label: "10x", value: 10 },
];

/** Month name abbreviations */
const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Dot configuration */
const DOT_SIZE = 3; // Base size in pixels
const PULSE_SIZE = 8; // Size during pulse animation
const PULSE_DURATION = 200; // Duration of pulse in ms
const HEAT_TRAIL_LENGTH = 20; // Number of recent dots at full opacity
const FADE_OPACITY = 0.6; // Opacity for older dots

/** Base delay between logs in ms (at 1x speed) */
const BASE_DELAY = 50;

interface DisplayedDot {
  x: number;
  y: number;
  colour: string;
  addedAt: number; // Timestamp when dot was added
}

export default function AnimatedUserMap({
  userId,
  autoPlay = true,
  height = 400,
}: AnimatedUserMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mapImageRef = useRef<HTMLImageElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  // Theme
  const { resolvedTheme } = useTheme();
  const mapColours = MAP_COLOURS[resolvedTheme];

  // State
  const [isPlaying, setIsPlaying] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [displayedDots, setDisplayedDots] = useState<DisplayedDot[]>([]);
  const [currentDate, setCurrentDate] = useState<string | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Fetch timeline data
  const { data: timeline, isLoading, error } = useUserLogTimeline(userId);

  // Calculate canvas dimensions maintaining aspect ratio
  const canvasWidth = useMemo(() => {
    return Math.round((height * MAP_DIMENSIONS.width) / MAP_DIMENSIONS.height);
  }, [height]);

  // Group logs by date for batching
  const logsByDate = useMemo(() => {
    if (!timeline) return new Map<string, TimelineEntry[]>();
    const grouped = new Map<string, TimelineEntry[]>();
    for (const entry of timeline) {
      const dateKey = entry.date || "unknown";
      const existing = grouped.get(dateKey) || [];
      existing.push(entry);
      grouped.set(dateKey, existing);
    }
    return grouped;
  }, [timeline]);

  // Get unique dates in order
  const orderedDates = useMemo(() => {
    if (!timeline) return [];
    const dates = new Set<string>();
    for (const entry of timeline) {
      dates.add(entry.date || "unknown");
    }
    return Array.from(dates);
  }, [timeline]);

  // Current year and month for display (e.g., "Nov 2024")
  const currentYearMonth = useMemo(() => {
    if (!currentDate || currentDate === "unknown") return null;
    const parts = currentDate.split("-");
    const year = parts[0];
    const monthNum = parseInt(parts[1], 10);
    const month = MONTH_NAMES[monthNum - 1] || "";
    return month ? `${month} ${year}` : year;
  }, [currentDate]);

  // Load map image
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      mapImageRef.current = img;
      setMapLoaded(true);
    };
    img.onerror = () => {
      console.error("Failed to load map image");
    };
    img.src = "/ukmap.png";
  }, []);

  // Play tick sound
  const playTick = useCallback(() => {
    if (!soundEnabled) return;

    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }
      const ctx = audioContextRef.current;
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      oscillator.frequency.value = 800;
      oscillator.type = "sine";

      gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);

      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + 0.05);
    } catch {
      // Audio not available
    }
  }, [soundEnabled]);

  // Create coloured version of map on an offscreen canvas
  const createColouredMap = useCallback(
    (
      image: HTMLImageElement,
      width: number,
      height: number,
      colour: string
    ): HTMLCanvasElement => {
      const offscreen = document.createElement("canvas");
      offscreen.width = width;
      offscreen.height = height;
      const offCtx = offscreen.getContext("2d");
      if (!offCtx) return offscreen;

      // Draw the map image
      offCtx.drawImage(image, 0, 0, width, height);

      // Use source-in to recolour just the opaque pixels
      offCtx.globalCompositeOperation = "source-in";
      offCtx.fillStyle = colour;
      offCtx.fillRect(0, 0, width, height);

      return offscreen;
    },
    []
  );

  // Draw the map and dots
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const mapImage = mapImageRef.current;

    if (!canvas || !ctx || !mapImage) return;

    // Clear canvas and fill with sea colour
    ctx.fillStyle = mapColours.sea;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw coastline (slightly expanded map in coastline colour)
    if (mapColours.coastlineWidth > 0) {
      const coastlineMap = createColouredMap(
        mapImage,
        canvas.width,
        canvas.height,
        mapColours.coastline
      );
      const expand = mapColours.coastlineWidth * 2;
      ctx.drawImage(
        coastlineMap,
        -expand / 2,
        -expand / 2,
        canvas.width + expand,
        canvas.height + expand
      );
    }

    // Draw land on top
    const landMap = createColouredMap(
      mapImage,
      canvas.width,
      canvas.height,
      mapColours.land
    );
    ctx.drawImage(landMap, 0, 0);

    const now = Date.now();

    // Draw all dots
    displayedDots.forEach((dot, index) => {
      const age = now - dot.addedAt;
      const isRecent = index >= displayedDots.length - HEAT_TRAIL_LENGTH;
      const isPulsing = age < PULSE_DURATION;

      // Calculate size (pulse effect for new dots)
      let size = DOT_SIZE;
      if (isPulsing) {
        const progress = age / PULSE_DURATION;
        size = PULSE_SIZE - (PULSE_SIZE - DOT_SIZE) * progress;
      }

      // Calculate opacity (heat trail effect)
      let opacity = isRecent ? 1 : FADE_OPACITY;
      if (isPulsing) {
        opacity = 1;
      }

      // Draw dot as square
      ctx.globalAlpha = opacity;
      ctx.fillStyle = dot.colour;
      ctx.fillRect(
        dot.x - size / 2,
        dot.y - size / 2,
        size,
        size
      );

      // Add glow effect for pulsing dots
      if (isPulsing) {
        ctx.globalAlpha = 0.3 * (1 - age / PULSE_DURATION);
        ctx.fillRect(
          dot.x - size,
          dot.y - size,
          size * 2,
          size * 2
        );
      }
    });

    ctx.globalAlpha = 1;
  }, [displayedDots, mapColours, createColouredMap]);

  // Redraw when dots change or theme changes
  useEffect(() => {
    if (mapLoaded) {
      draw();
    }
  }, [draw, mapLoaded, displayedDots, mapColours]);

  // Animation loop - process next batch of logs
  const processNextBatch = useCallback(() => {
    if (!timeline || currentIndex >= orderedDates.length) {
      return false; // Signal completion
    }

    const dateKey = orderedDates[currentIndex];
    const logsForDate = logsByDate.get(dateKey) || [];

    // Add all dots for this date
    const newDots: DisplayedDot[] = logsForDate.map((entry) => {
      const pixel = latLonToScaledPixel(
        entry.lat,
        entry.lon,
        canvasWidth,
        height
      );
      return {
        x: pixel.x,
        y: pixel.y,
        colour: getLogColourHex(entry.colour),
        addedAt: Date.now(),
      };
    });

    if (newDots.length > 0) {
      setDisplayedDots((prev) => [...prev, ...newDots]);
      setCurrentDate(dateKey);
      playTick();
    }

    setCurrentIndex((prev) => prev + 1);
    return true; // More to process
  }, [timeline, currentIndex, orderedDates, logsByDate, canvasWidth, height, playTick]);

  // Animation timer
  useEffect(() => {
    if (!isPlaying) return;

    // Check if we're done - use setTimeout to avoid setState in effect body
    if (currentIndex >= orderedDates.length) {
      setTimeout(() => {
        setIsPlaying(false);
        setIsComplete(true);
      }, 0);
      return;
    }

    // Schedule next batch
    const delay = BASE_DELAY / speed;
    const timeoutId = setTimeout(() => {
      processNextBatch();
    }, delay);

    return () => clearTimeout(timeoutId);
  }, [isPlaying, currentIndex, orderedDates.length, speed, processNextBatch]);

  // Continuous redraw for pulse animations
  useEffect(() => {
    if (!mapLoaded) return;

    let animationId: number;
    const animate = () => {
      draw();
      animationId = requestAnimationFrame(animate);
    };

    // Only run animation loop when there are recent dots
    const hasRecentDots = displayedDots.some(
      (dot) => Date.now() - dot.addedAt < PULSE_DURATION
    );

    if (hasRecentDots || isPlaying) {
      animationId = requestAnimationFrame(animate);
    }

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [draw, displayedDots, isPlaying, mapLoaded]);

  // Auto-play on mount - using a ref to track if we've already started
  const hasAutoPlayed = useRef(false);
  useEffect(() => {
    if (autoPlay && timeline && timeline.length > 0 && mapLoaded && !isComplete && !hasAutoPlayed.current) {
      hasAutoPlayed.current = true;
      // Use setTimeout to avoid setState warning in effect
      setTimeout(() => setIsPlaying(true), 0);
    }
  }, [autoPlay, timeline, mapLoaded, isComplete]);

  // Handlers
  const handlePlayPause = () => {
    if (isComplete) {
      // Reset and play
      setDisplayedDots([]);
      setCurrentIndex(0);
      setCurrentDate(null);
      setIsComplete(false);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleReplay = () => {
    setDisplayedDots([]);
    setCurrentIndex(0);
    setCurrentDate(null);
    setIsComplete(false);
    setIsPlaying(true);
  };

  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(newSpeed);
  };

  const handleScrub = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timeline || orderedDates.length === 0) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const progress = x / rect.width;
    const targetIndex = Math.floor(progress * orderedDates.length);

    // Rebuild dots up to target index
    const newDots: DisplayedDot[] = [];
    for (let i = 0; i <= targetIndex && i < orderedDates.length; i++) {
      const dateKey = orderedDates[i];
      const logsForDate = logsByDate.get(dateKey) || [];
      for (const entry of logsForDate) {
        const pixel = latLonToScaledPixel(
          entry.lat,
          entry.lon,
          canvasWidth,
          height
        );
        newDots.push({
          x: pixel.x,
          y: pixel.y,
          colour: getLogColourHex(entry.colour),
          addedAt: Date.now() - PULSE_DURATION, // Don't pulse
        });
      }
    }

    setDisplayedDots(newDots);
    setCurrentIndex(targetIndex + 1);
    setCurrentDate(orderedDates[targetIndex] || null);
    setIsComplete(targetIndex >= orderedDates.length - 1);
    setIsPlaying(false);
  };

  // Jump to a specific index and rebuild dots
  // overrideDate: if provided, display this date instead of the actual log date
  const jumpToIndex = useCallback(
    (targetIndex: number, overrideDate?: string) => {
      if (!timeline || orderedDates.length === 0) return;

      // Clamp to valid range
      const clampedIndex = Math.max(0, Math.min(targetIndex, orderedDates.length - 1));

      // Rebuild dots up to target index
      const newDots: DisplayedDot[] = [];
      for (let i = 0; i <= clampedIndex && i < orderedDates.length; i++) {
        const dateKey = orderedDates[i];
        const logsForDate = logsByDate.get(dateKey) || [];
        for (const entry of logsForDate) {
          const pixel = latLonToScaledPixel(
            entry.lat,
            entry.lon,
            canvasWidth,
            height
          );
          newDots.push({
            x: pixel.x,
            y: pixel.y,
            colour: getLogColourHex(entry.colour),
            addedAt: Date.now() - PULSE_DURATION, // Don't pulse
          });
        }
      }

      setDisplayedDots(newDots);
      setCurrentIndex(clampedIndex + 1);
      setCurrentDate(overrideDate || orderedDates[clampedIndex] || null);
      setIsComplete(clampedIndex >= orderedDates.length - 1);
      setIsPlaying(false);
    },
    [timeline, orderedDates, logsByDate, canvasWidth, height]
  );

  // Skip by year (direction: -1 for back, +1 for forward)
  // Shows the target date (current + direction years) regardless of actual log dates
  const skipByYear = useCallback(
    (direction: number) => {
      if (!orderedDates.length) return;

      // Get current date components (use first log date if not started)
      const baseDateKey = currentDate || orderedDates[0];
      if (!baseDateKey || baseDateKey === "unknown") return;

      const [yearStr, monthStr] = baseDateKey.split("-");
      const baseYear = parseInt(yearStr, 10);
      const baseMonth = monthStr || "01";

      // Calculate target date
      const targetYear = baseYear + direction;
      const targetDateKey = `${targetYear}-${baseMonth}`;

      if (direction < 0) {
        // Going backwards: find last log that is <= target date
        let targetIdx = -1;
        for (let i = orderedDates.length - 1; i >= 0; i--) {
          const d = orderedDates[i];
          if (d && d !== "unknown" && d <= targetDateKey) {
            targetIdx = i;
            break;
          }
        }
        if (targetIdx !== -1) {
          jumpToIndex(targetIdx, targetDateKey);
        } else {
          // No logs before target, jump to start but show target date
          jumpToIndex(0, targetDateKey);
        }
      } else {
        // Going forwards: find last log that is <= target date
        let targetIdx = -1;
        for (let i = orderedDates.length - 1; i >= 0; i--) {
          const d = orderedDates[i];
          if (d && d !== "unknown" && d <= targetDateKey) {
            targetIdx = i;
            break;
          }
        }
        if (targetIdx !== -1) {
          jumpToIndex(targetIdx, targetDateKey);
        } else {
          // Target is before all logs, show no dots but display target date
          setDisplayedDots([]);
          setCurrentIndex(0);
          setCurrentDate(targetDateKey);
          setIsComplete(false);
          setIsPlaying(false);
        }
      }
    },
    [orderedDates, currentDate, jumpToIndex]
  );

  // Skip by month (direction: -1 for back, +1 for forward)
  // Shows the target date (current + direction months) regardless of actual log dates
  const skipByMonth = useCallback(
    (direction: number) => {
      if (!orderedDates.length) return;

      // Get current date components (use first log date if not started)
      const baseDateKey = currentDate || orderedDates[0];
      if (!baseDateKey || baseDateKey === "unknown") return;

      const [yearStr, monthStr] = baseDateKey.split("-");
      let baseYear = parseInt(yearStr, 10);
      let baseMonth = parseInt(monthStr || "1", 10);

      // Calculate target month/year
      baseMonth += direction;
      if (baseMonth > 12) {
        baseMonth = 1;
        baseYear += 1;
      } else if (baseMonth < 1) {
        baseMonth = 12;
        baseYear -= 1;
      }

      const targetDateKey = `${baseYear}-${String(baseMonth).padStart(2, "0")}`;

      if (direction < 0) {
        // Going backwards: find last log that is <= target date
        let targetIdx = -1;
        for (let i = orderedDates.length - 1; i >= 0; i--) {
          const d = orderedDates[i];
          if (d && d !== "unknown" && d <= targetDateKey + "-31") {
            targetIdx = i;
            break;
          }
        }
        if (targetIdx !== -1) {
          jumpToIndex(targetIdx, targetDateKey);
        } else {
          // No logs before target, show no dots but display target date
          setDisplayedDots([]);
          setCurrentIndex(0);
          setCurrentDate(targetDateKey);
          setIsComplete(false);
          setIsPlaying(false);
        }
      } else {
        // Going forwards: find last log that is <= end of target month
        let targetIdx = -1;
        for (let i = orderedDates.length - 1; i >= 0; i--) {
          const d = orderedDates[i];
          if (d && d !== "unknown" && d <= targetDateKey + "-31") {
            targetIdx = i;
            break;
          }
        }
        if (targetIdx !== -1) {
          jumpToIndex(targetIdx, targetDateKey);
        } else {
          // Target is before all logs, show no dots but display target date
          setDisplayedDots([]);
          setCurrentIndex(0);
          setCurrentDate(targetDateKey);
          setIsComplete(false);
          setIsPlaying(false);
        }
      }
    },
    [orderedDates, currentDate, jumpToIndex]
  );

  // Skip to end (present day / most recent log)
  const skipToEnd = useCallback(() => {
    if (orderedDates.length > 0) {
      jumpToIndex(orderedDates.length - 1);
    }
  }, [orderedDates, jumpToIndex]);

  // Loading state
  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg"
        style={{ height, width: canvasWidth }}
      >
        <Spinner size="lg" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg text-red-500"
        style={{ height, width: canvasWidth }}
      >
        Failed to load timeline
      </div>
    );
  }

  // Empty state
  if (!timeline || timeline.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-500 dark:text-gray-400"
        style={{ height, width: canvasWidth }}
      >
        No logs to display
      </div>
    );
  }

  // Calculate progress
  const progress =
    orderedDates.length > 0 ? currentIndex / orderedDates.length : 0;

  // Date range for display
  const firstDate = orderedDates[0];
  const lastDate = orderedDates[orderedDates.length - 1];

  return (
    <div className="relative" style={{ width: canvasWidth }}>
      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={height}
        className="rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900"
      />

      {/* Year/Month overlay */}
      {currentYearMonth && (
        <div className="absolute top-3 left-3 bg-black/60 text-white px-3 py-1 rounded-md font-mono text-2xl font-bold">
          {currentYearMonth}
        </div>
      )}

      {/* Stats overlay */}
      <div className="absolute top-3 right-3 bg-black/60 text-white px-3 py-1 rounded-md text-sm">
        <span className="font-bold">{displayedDots.length}</span>
        <span className="text-gray-300"> / {timeline.length} logs</span>
      </div>

      {/* Timeline scrubber */}
      <div
        className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full cursor-pointer overflow-hidden"
        onClick={handleScrub}
      >
        <div
          className="h-full bg-trig-green-600 transition-all duration-100"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      {/* Date range labels */}
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
        <span>{firstDate !== "unknown" ? firstDate : "—"}</span>
        <span>{lastDate !== "unknown" ? lastDate : "—"}</span>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mt-3 gap-2 flex-wrap">
        {/* Play/Pause and Replay */}
        <div className="flex items-center gap-1">
          <button
            onClick={handlePlayPause}
            className="p-2 rounded-full bg-trig-green-600 text-white hover:bg-trig-green-700 transition-colors"
            aria-label={isPlaying ? "Pause" : isComplete ? "Replay" : "Play"}
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Skip controls: |< <<year <month | month> year>> >| */}
        <div className="flex items-center gap-0.5">
          <button
            onClick={handleReplay}
            className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            aria-label="Skip to start"
            title="Skip to start"
          >
            <SkipBack className="w-4 h-4" />
          </button>
          <button
            onClick={() => skipByYear(-1)}
            className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            aria-label="Skip back one year"
            title="Year back"
          >
            <ChevronsLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => skipByMonth(-1)}
            className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            aria-label="Skip back one month"
            title="Month back"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => skipByMonth(1)}
            className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            aria-label="Skip forward one month"
            title="Month forward"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => skipByYear(1)}
            className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            aria-label="Skip forward one year"
            title="Year forward"
          >
            <ChevronsRight className="w-4 h-4" />
          </button>
          <button
            onClick={skipToEnd}
            className="p-1.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            aria-label="Skip to end"
            title="Skip to present"
          >
            <SkipForward className="w-4 h-4" />
          </button>
        </div>

        {/* Speed selector */}
        <div className="flex items-center gap-1">
          {SPEED_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => handleSpeedChange(option.value)}
              className={`px-2 py-1 text-sm rounded transition-colors ${
                speed === option.value
                  ? "bg-trig-green-600 text-white"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        {/* Sound toggle */}
        <button
          onClick={() => setSoundEnabled(!soundEnabled)}
          className={`p-2 rounded-full transition-colors ${
            soundEnabled
              ? "bg-trig-green-600 text-white"
              : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
          }`}
          aria-label={soundEnabled ? "Mute" : "Unmute"}
        >
          {soundEnabled ? (
            <Volume2 className="w-5 h-5" />
          ) : (
            <VolumeX className="w-5 h-5" />
          )}
        </button>
      </div>
    </div>
  );
}

