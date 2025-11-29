import { wgs84ToOSGB } from "./coordinates";

export interface ParsedLocation {
  eastings: number;
  northings: number;
  gridRef: string;
  lat?: number;
  lon?: number;
}

export interface ParseResult {
  success: boolean;
  data?: ParsedLocation;
  error?: string;
}

/**
 * Convert a grid reference string to eastings and northings
 * Handles 6, 8, and 10 digit grid references
 */
export function gridRefToEastingsNorthings(gridRef: string): ParsedLocation {
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
  // The OSGB grid uses a 500km square system
  // Letters are arranged in a grid (omitting I):
  // HL HM HN HO HP  JL JM JN JO JP
  // HQ HR HS HT HU  JQ JR JS JT JU
  // HV HW HX HY HZ  JV JW JX JY JZ
  // NA NB NC ND NE  OA OB OC OD OE
  // NF NG NH NJ NK  OF OG OH OJ OK
  // NL NM NN NO NP  OL OM ON OO OP
  // NQ NR NS NT NU  OQ OR OS OT OU
  // NV NW NX NY NZ  OV OW OX OY OZ
  // SA SB SC SD SE  TA TB TC TD TE
  // SF SG SH SJ SK  TF TG TH TJ TK
  // SL SM SN SO SP  TL TM TN TO TP
  // SQ SR SS ST SU  TQ TR TS TT TU
  // SV SW SX SY SZ  TV TW TX TY TZ
  
  // Map first letter to 500km easting and northing offsets
  const firstLetterOffsets: Record<string, { e500: number; n500: number }> = {
    S: { e500: 0, n500: 0 },   // SW England
    T: { e500: 1, n500: 0 },   // SE England
    N: { e500: 0, n500: 1 },   // NW England/S Scotland
    O: { e500: 1, n500: 1 },   // NE England/S Scotland  
    H: { e500: 0, n500: 2 },   // NW Scotland
    J: { e500: 1, n500: 2 },   // NE Scotland
  };

  if (!(firstLetter in firstLetterOffsets)) {
    throw new Error(`Invalid first letter in grid reference: ${firstLetter}`);
  }

  // Second letter: 100km squares within 500km square (5x5 grid, omitting I)
  // Letters go: VWXYZ, QRSTU, LMNOP, FGHJK, ABCDE (top to bottom, left to right)
  // Row 4 (north): V W X Y Z
  // Row 3:        Q R S T U
  // Row 2:        L M N O P
  // Row 1:        F G H J K
  // Row 0 (south): A B C D E
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

  // Calculate the 100km square indices
  // Each 500km square contains a 5x5 grid of 100km squares
  // n100km within the 500km square = (4 - row) because rows go north to south
  // e100km within the 500km square = col
  const n100kmWithin500 = 4 - secondIndex.row;
  const e100kmWithin500 = secondIndex.col;
  
  // Add the 500km offsets (each 500km square contains 5x100km squares)
  const n100km = firstOffsets.n500 * 5 + n100kmWithin500;
  const e100km = firstOffsets.e500 * 5 + e100kmWithin500;

  // Calculate full coordinates
  const eastings = e100km * 100000 + parseInt(ePadded, 10);
  const northings = n100km * 100000 + parseInt(nPadded, 10);

  // Format the normalized grid reference with spaces
  const normalizedGridRef = `${letters} ${ePadded} ${nPadded}`;

  return {
    eastings,
    northings,
    gridRef: normalizedGridRef,
  };
}

/**
 * Parse a grid reference string
 * Accepts formats like: TL137055, TL 137 055, TL13780553, TL 1378305532
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
 * Parse lat/long coordinates
 * Accepts format: "53.69417, -1.78231" or "53.69417,-1.78231"
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

  try {
    // Convert to OSGB
    const { eastings, northings, gridRef } = wgs84ToOSGB(lat, lon);

    return {
      success: true,
      data: {
        eastings,
        northings,
        gridRef,
        lat,
        lon,
      },
    };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : "Failed to convert coordinates to OSGB",
    };
  }
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

  // Try grid reference first
  const gridResult = parseGridReference(input);
  if (gridResult.success) {
    return gridResult;
  }

  // Try lat/long
  const latLongResult = parseLatLong(input);
  if (latLongResult.success) {
    return latLongResult;
  }

  // Both failed - return a generic error
  return {
    success: false,
    error: "Invalid location format. Use grid reference (e.g., TL 137 055) or coordinates (e.g., 53.69417, -1.78231)",
  };
}
