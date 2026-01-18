import { convertCoordinates } from "./api";

export type GridSystem = 'gb' | 'ie' | null;

export interface ParsedLocation {
  eastings: number;
  northings: number;
  gridRef: string;
  lat?: number;
  lon?: number;
  /** Grid system: 'gb' for British National Grid, 'ie' for Irish Grid */
  gridSystem?: GridSystem;
}

export interface ParseResult {
  success: boolean;
  data?: ParsedLocation;
  error?: string;
}

/**
 * Check if a string looks like an Irish Grid reference (single letter + digits)
 */
export function isIrishGridRef(input: string): boolean {
  const cleaned = input.replace(/\s+/g, "").toUpperCase();
  return /^[A-HJ-Z]\d+$/.test(cleaned);
}

/**
 * Check if a string looks like an OSGB Grid reference (two letters + digits)
 */
export function isOsgbGridRef(input: string): boolean {
  const cleaned = input.replace(/\s+/g, "").toUpperCase();
  return /^[A-Z]{2}\d+$/.test(cleaned);
}

/**
 * Convert an Irish grid reference string to eastings and northings
 * Handles 6, 8, and 10 digit grid references
 */
export function irishGridRefToEastingsNorthings(gridRef: string): ParsedLocation {
  const cleaned = gridRef.replace(/\s+/g, "").toUpperCase();

  // Irish grid reference: single letter followed by 6, 8, or 10 digits
  const match = cleaned.match(/^([A-HJ-Z])(\d+)$/);
  if (!match) {
    throw new Error("Invalid Irish grid reference format");
  }

  const [, letter, digits] = match;

  // Check digit count is even and valid
  if (digits.length % 2 !== 0 || digits.length < 6 || digits.length > 10) {
    throw new Error("Irish grid reference must have 6, 8, or 10 digits");
  }

  const halfLen = digits.length / 2;
  const eDigits = digits.substring(0, halfLen);
  const nDigits = digits.substring(halfLen);

  // Pad to 5 digits with trailing zeros for full precision
  const ePadded = eDigits.padEnd(5, "0");
  const nPadded = nDigits.padEnd(5, "0");

  // Irish Grid uses a single letter in a 5x5 grid (A-Z excluding I)
  // Origin is at the southwest
  // V W X Y Z (row 0, N 0-100km)
  // Q R S T U (row 1, N 100-200km)
  // L M N O P (row 2, N 200-300km)
  // F G H J K (row 3, N 300-400km, skips I)
  // A B C D E (row 4, N 400-500km)
  const irishGridLetters: Record<string, { e100: number; n100: number }> = {
    A: { e100: 0, n100: 4 }, B: { e100: 1, n100: 4 }, C: { e100: 2, n100: 4 }, D: { e100: 3, n100: 4 }, E: { e100: 4, n100: 4 },
    F: { e100: 0, n100: 3 }, G: { e100: 1, n100: 3 }, H: { e100: 2, n100: 3 }, J: { e100: 3, n100: 3 }, K: { e100: 4, n100: 3 },
    L: { e100: 0, n100: 2 }, M: { e100: 1, n100: 2 }, N: { e100: 2, n100: 2 }, O: { e100: 3, n100: 2 }, P: { e100: 4, n100: 2 },
    Q: { e100: 0, n100: 1 }, R: { e100: 1, n100: 1 }, S: { e100: 2, n100: 1 }, T: { e100: 3, n100: 1 }, U: { e100: 4, n100: 1 },
    V: { e100: 0, n100: 0 }, W: { e100: 1, n100: 0 }, X: { e100: 2, n100: 0 }, Y: { e100: 3, n100: 0 }, Z: { e100: 4, n100: 0 },
  };

  if (!(letter in irishGridLetters)) {
    throw new Error(`Invalid letter in Irish grid reference: ${letter}`);
  }

  const offsets = irishGridLetters[letter];
  const eastings = offsets.e100 * 100000 + parseInt(ePadded, 10);
  const northings = offsets.n100 * 100000 + parseInt(nPadded, 10);

  // Format the normalized grid reference with spaces
  const normalizedGridRef = `${letter} ${ePadded} ${nPadded}`;

  return {
    eastings,
    northings,
    gridRef: normalizedGridRef,
    gridSystem: 'ie',
  };
}

/**
 * Convert an OSGB grid reference string to eastings and northings
 * Handles 6, 8, and 10 digit grid references
 */
export function osgbGridRefToEastingsNorthings(gridRef: string): ParsedLocation {
  // Remove spaces and convert to uppercase
  const cleaned = gridRef.replace(/\s+/g, "").toUpperCase();

  // Grid reference should be 2 letters followed by 6, 8, or 10 digits
  const match = cleaned.match(/^([A-Z]{2})(\d+)$/);
  if (!match) {
    throw new Error("Invalid grid reference format");
  }

  const [, letters, digits] = match;

  // Check digit count is even and valid (6, 8, or 10)
  if (digits.length % 2 !== 0 || digits.length < 6 || digits.length > 10) {
    throw new Error("Grid reference must have 6, 8, or 10 digits");
  }

  const halfLen = digits.length / 2;
  const eDigits = digits.substring(0, halfLen);
  const nDigits = digits.substring(halfLen);

  // Pad to 5 digits with trailing zeros for full precision
  const ePadded = eDigits.padEnd(5, "0");
  const nPadded = nDigits.padEnd(5, "0");

  // Decode the two-letter grid square
  const firstLetter = letters.charAt(0);
  const secondLetter = letters.charAt(1);

  // First letter: 500km squares
  const firstLetterOffsets: Record<string, { e500: number; n500: number }> = {
    S: { e500: 0, n500: 0 },
    T: { e500: 1, n500: 0 },
    N: { e500: 0, n500: 1 },
    O: { e500: 1, n500: 1 },
    H: { e500: 0, n500: 2 },
    J: { e500: 1, n500: 2 },
  };

  if (!(firstLetter in firstLetterOffsets)) {
    throw new Error(`Invalid first letter in grid reference: ${firstLetter}`);
  }

  // Second letter: 100km squares within 500km square (5x5 grid, omitting I)
  const secondLetterToRowCol: Record<string, { row: number; col: number }> = {
    V: { row: 4, col: 0 },
    W: { row: 4, col: 1 },
    X: { row: 4, col: 2 },
    Y: { row: 4, col: 3 },
    Z: { row: 4, col: 4 },
    Q: { row: 3, col: 0 },
    R: { row: 3, col: 1 },
    S: { row: 3, col: 2 },
    T: { row: 3, col: 3 },
    U: { row: 3, col: 4 },
    L: { row: 2, col: 0 },
    M: { row: 2, col: 1 },
    N: { row: 2, col: 2 },
    O: { row: 2, col: 3 },
    P: { row: 2, col: 4 },
    F: { row: 1, col: 0 },
    G: { row: 1, col: 1 },
    H: { row: 1, col: 2 },
    J: { row: 1, col: 3 },
    K: { row: 1, col: 4 },
    A: { row: 0, col: 0 },
    B: { row: 0, col: 1 },
    C: { row: 0, col: 2 },
    D: { row: 0, col: 3 },
    E: { row: 0, col: 4 },
  };

  if (!(secondLetter in secondLetterToRowCol)) {
    throw new Error(`Invalid second letter in grid reference: ${secondLetter}`);
  }

  const firstOffsets = firstLetterOffsets[firstLetter];
  const secondIndex = secondLetterToRowCol[secondLetter];

  const n100kmWithin500 = 4 - secondIndex.row;
  const e100kmWithin500 = secondIndex.col;

  const n100km = firstOffsets.n500 * 5 + n100kmWithin500;
  const e100km = firstOffsets.e500 * 5 + e100kmWithin500;

  const eastings = e100km * 100000 + parseInt(ePadded, 10);
  const northings = n100km * 100000 + parseInt(nPadded, 10);

  const normalizedGridRef = `${letters} ${ePadded} ${nPadded}`;

  return {
    eastings,
    northings,
    gridRef: normalizedGridRef,
    gridSystem: 'gb',
  };
}

/**
 * Convert a grid reference string to eastings and northings.
 * Automatically detects OSGB (2 letters) vs Irish Grid (1 letter) format.
 */
export function gridRefToEastingsNorthings(gridRef: string): ParsedLocation {
  const cleaned = gridRef.replace(/\s+/g, "").toUpperCase();

  // Try Irish Grid first (single letter)
  if (isIrishGridRef(cleaned)) {
    return irishGridRefToEastingsNorthings(gridRef);
  }

  // Try OSGB (two letters)
  if (isOsgbGridRef(cleaned)) {
    return osgbGridRefToEastingsNorthings(gridRef);
  }

  throw new Error("Invalid grid reference format");
}

/**
 * Parse a grid reference string.
 * Accepts formats like: TL137055, TL 137 055, O123456, O 123 456
 */
export function parseGridReference(input: string): ParseResult {
  try {
    const data = gridRefToEastingsNorthings(input);
    return {
      success: true,
      data,
    };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error ? error.message : "Invalid grid reference format",
    };
  }
}

/**
 * Parse lat/long coordinates and convert to grid coordinates using the backend API.
 * The backend auto-detects whether to use OSGB36 or Irish Grid based on location.
 * Accepts format: "53.69417, -1.78231" or "53.69417,-1.78231"
 */
export async function parseLatLongAsync(input: string): Promise<ParseResult> {
  // Split by comma
  const parts = input.split(",").map((s) => s.trim());

  if (parts.length !== 2) {
    return {
      success: false,
      error: "Coordinates must be in format: latitude, longitude",
    };
  }

  const lat = parseFloat(parts[0]);
  const lon = parseFloat(parts[1]);

  if (isNaN(lat) || isNaN(lon)) {
    return {
      success: false,
      error: "Invalid coordinates format",
    };
  }

  // Validate ranges
  if (lat < -90 || lat > 90) {
    return {
      success: false,
      error: "Latitude must be between -90 and 90",
    };
  }

  if (lon < -180 || lon > 180) {
    return {
      success: false,
      error: "Longitude must be between -180 and 180",
    };
  }

  try {
    // Use backend API for coordinate conversion with auto-detection
    const result = await convertCoordinates({
      from: "wgs84",
      to: "grid",  // Auto-detect GB vs Irish Grid
      lat,
      lon,
    });

    const gridSystem = result.grid_system as GridSystem;

    return {
      success: true,
      data: {
        eastings: result.output.e ?? 0,
        northings: result.output.n ?? 0,
        gridRef: result.output.gridref ?? "",
        lat,
        lon,
        gridSystem,
      },
    };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : "Failed to convert coordinates",
    };
  }
}

/**
 * Parse lat/long coordinates (synchronous version).
 * This version returns immediately and doesn't call the backend API.
 * Use parseLatLongAsync for full coordinate conversion including Irish Grid support.
 */
export function parseLatLong(input: string): ParseResult {
  // Split by comma
  const parts = input.split(",").map((s) => s.trim());

  if (parts.length !== 2) {
    return {
      success: false,
      error: "Coordinates must be in format: latitude, longitude",
    };
  }

  const lat = parseFloat(parts[0]);
  const lon = parseFloat(parts[1]);

  if (isNaN(lat) || isNaN(lon)) {
    return {
      success: false,
      error: "Invalid coordinates format",
    };
  }

  // Validate ranges
  if (lat < -90 || lat > 90) {
    return {
      success: false,
      error: "Latitude must be between -90 and 90",
    };
  }

  if (lon < -180 || lon > 180) {
    return {
      success: false,
      error: "Longitude must be between -180 and 180",
    };
  }

  // Return success with lat/lon but without grid coordinates
  // The caller should use parseLatLongAsync for full conversion
  return {
    success: true,
    data: {
      eastings: 0,  // Not available synchronously
      northings: 0,  // Not available synchronously
      gridRef: "",  // Not available synchronously
      lat,
      lon,
      gridSystem: null,
    },
  };
}

/**
 * Parse location input - tries grid reference first, then lat/long
 */
export function parseLocation(input: string): ParseResult {
  // Empty input is not an error, just no location
  if (!input || input.trim() === "") {
    return {
      success: false,
      error: "",
    };
  }

  // Try grid reference first (handles both OSGB and Irish Grid)
  const gridResult = parseGridReference(input);
  if (gridResult.success) {
    return gridResult;
  }

  // Try lat/long (synchronous - returns lat/lon without grid conversion)
  const latLongResult = parseLatLong(input);
  if (latLongResult.success) {
    return latLongResult;
  }

  // Both failed - return a generic error
  return {
    success: false,
    error: "Invalid location format. Use grid reference (e.g., TL 137 055 or O 123 456) or coordinates (e.g., 53.69417, -1.78231)",
  };
}

/**
 * Parse location input with async lat/long conversion.
 * Use this when you need full grid coordinate conversion for lat/long inputs.
 */
export async function parseLocationAsync(input: string): Promise<ParseResult> {
  // Empty input is not an error, just no location
  if (!input || input.trim() === "") {
    return {
      success: false,
      error: "",
    };
  }

  // Try grid reference first (handles both OSGB and Irish Grid)
  const gridResult = parseGridReference(input);
  if (gridResult.success) {
    return gridResult;
  }

  // Try lat/long with async API conversion
  const latLongResult = await parseLatLongAsync(input);
  if (latLongResult.success) {
    return latLongResult;
  }

  // Both failed - return a generic error
  return {
    success: false,
    error: "Invalid location format. Use grid reference (e.g., TL 137 055 or O 123 456) or coordinates (e.g., 53.69417, -1.78231)",
  };
}
