/**
 * Calculate distance between two WGS84 coordinates using Haversine formula
 * Returns distance in meters
 */
export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000; // Earth's radius in meters
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; // Distance in meters
}

/**
 * Convert WGS84 lat/lon to OSGB36 Eastings/Northings using Helmert transformation
 * Based on Ordnance Survey's conversion equations
 * 
 * This is a simplified implementation suitable for GB. For high precision
 * surveying, use the OS transformation libraries.
 */

interface OSGBCoordinates {
  eastings: number;
  northings: number;
  gridRef: string;
}

/**
 * Convert WGS84 coordinates to OSGB36 grid reference
 */
export function wgs84ToOSGB(lat: number, lon: number): OSGBCoordinates {
  // WGS84 parameters
  const a_wgs = 6378137.0; // semi-major axis
  const b_wgs = 6356752.314; // semi-minor axis
  const e2_wgs = 1 - (b_wgs * b_wgs) / (a_wgs * a_wgs);

  // OSGB36 parameters
  const a_osgb = 6377563.396;
  const b_osgb = 6356256.909;
  const e2_osgb = 1 - (b_osgb * b_osgb) / (a_osgb * a_osgb);

  // Helmert transformation parameters (WGS84 to OSGB36)
  const tx = -446.448; // metres
  const ty = 125.157;
  const tz = -542.060;
  const rx = -0.1502; // seconds
  const ry = -0.2470;
  const rz = -0.8421;
  const s = 20.4894; // ppm

  // Convert to radians
  const latRad = (lat * Math.PI) / 180;
  const lonRad = (lon * Math.PI) / 180;

  // Convert to Cartesian coordinates (WGS84)
  const nu = a_wgs / Math.sqrt(1 - e2_wgs * Math.sin(latRad) * Math.sin(latRad));
  const x1 = nu * Math.cos(latRad) * Math.cos(lonRad);
  const y1 = nu * Math.cos(latRad) * Math.sin(lonRad);
  const z1 = (1 - e2_wgs) * nu * Math.sin(latRad);

  // Apply Helmert transformation
  const rxRad = (rx / 3600) * (Math.PI / 180);
  const ryRad = (ry / 3600) * (Math.PI / 180);
  const rzRad = (rz / 3600) * (Math.PI / 180);
  const s1 = s / 1e6 + 1;

  const x2 = tx + x1 * s1 - y1 * rzRad + z1 * ryRad;
  const y2 = ty + x1 * rzRad + y1 * s1 - z1 * rxRad;
  const z2 = tz - x1 * ryRad + y1 * rxRad + z1 * s1;

  // Convert back to lat/lon (OSGB36)
  const p = Math.sqrt(x2 * x2 + y2 * y2);
  let latOsgb = Math.atan2(z2, p * (1 - e2_osgb));

  // Iterate to improve accuracy
  for (let i = 0; i < 10; i++) {
    const nu2 = a_osgb / Math.sqrt(1 - e2_osgb * Math.sin(latOsgb) * Math.sin(latOsgb));
    latOsgb = Math.atan2(z2 + e2_osgb * nu2 * Math.sin(latOsgb), p);
  }

  const lonOsgb = Math.atan2(y2, x2);

  // Convert to National Grid (Transverse Mercator projection)
  const lat0 = (49 * Math.PI) / 180; // True origin latitude
  const lon0 = (-2 * Math.PI) / 180; // True origin longitude
  const N0 = -100000; // Northing of true origin
  const E0 = 400000; // Easting of true origin
  const F0 = 0.9996012717; // Scale factor on central meridian

  const n = (a_osgb - b_osgb) / (a_osgb + b_osgb);
  const n2 = n * n;
  const n3 = n * n * n;

  const cosLat = Math.cos(latOsgb);
  const sinLat = Math.sin(latOsgb);
  const nu3 = a_osgb * F0 / Math.sqrt(1 - e2_osgb * sinLat * sinLat);
  const rho = a_osgb * F0 * (1 - e2_osgb) / Math.pow(1 - e2_osgb * sinLat * sinLat, 1.5);
  const eta2 = nu3 / rho - 1;

  const M =
    b_osgb *
    F0 *
    ((1 + n + (5 / 4) * n2 + (5 / 4) * n3) * (latOsgb - lat0) -
      (3 * n + 3 * n2 + (21 / 8) * n3) * Math.sin(latOsgb - lat0) * Math.cos(latOsgb + lat0) +
      ((15 / 8) * n2 + (15 / 8) * n3) * Math.sin(2 * (latOsgb - lat0)) * Math.cos(2 * (latOsgb + lat0)) -
      ((35 / 24) * n3) * Math.sin(3 * (latOsgb - lat0)) * Math.cos(3 * (latOsgb + lat0)));

  const I = M + N0;
  const II = (nu3 / 2) * sinLat * cosLat;
  const III = (nu3 / 24) * sinLat * Math.pow(cosLat, 3) * (5 - Math.pow(Math.tan(latOsgb), 2) + 9 * eta2);
  const IIIA = (nu3 / 720) * sinLat * Math.pow(cosLat, 5) * (61 - 58 * Math.pow(Math.tan(latOsgb), 2) + Math.pow(Math.tan(latOsgb), 4));

  const IV = nu3 * cosLat;
  const V = (nu3 / 6) * Math.pow(cosLat, 3) * (nu3 / rho - Math.pow(Math.tan(latOsgb), 2));
  const VI = (nu3 / 120) * Math.pow(cosLat, 5) * (5 - 18 * Math.pow(Math.tan(latOsgb), 2) + Math.pow(Math.tan(latOsgb), 4) + 14 * eta2 - 58 * Math.pow(Math.tan(latOsgb), 2) * eta2);

  const dLon = lonOsgb - lon0;
  const dLon2 = dLon * dLon;
  const dLon3 = dLon2 * dLon;
  const dLon4 = dLon3 * dLon;
  const dLon5 = dLon4 * dLon;
  const dLon6 = dLon5 * dLon;

  const northings = Math.round(I + II * dLon2 + III * dLon4 + IIIA * dLon6);
  const eastings = Math.round(E0 + IV * dLon + V * dLon3 + VI * dLon5);

  // Convert to grid reference
  const gridRef = eastingsNorthingsToGridRef(eastings, northings);

  return {
    eastings,
    northings,
    gridRef,
  };
}

/**
 * Convert eastings/northings to OS grid reference string (e.g., "TL 12345 67890")
 */
function eastingsNorthingsToGridRef(eastings: number, northings: number): string {
  // OSGB grid is based on 500km and 100km squares
  // The grid extends from (0,0) at the SW corner to (700000, 1300000)
  
  const e100km = Math.floor(eastings / 100000);
  const n100km = Math.floor(northings / 100000);

  // Check bounds
  if (e100km < 0 || e100km > 6 || n100km < 0 || n100km > 12) {
    throw new Error("Coordinates outside GB grid");
  }

  // First letter: 500km squares (5x5 grid, but I is omitted)
  // Grid is arranged as: VWXYZ, QRSTU, LMNOP, FGHJK, ABCDE (north to south)
  const firstLetters = "STNOHJ"; // Maps 500km northing divisions
  const firstLetterIndex = Math.floor(n100km / 5);
  const firstLetter = firstLetters.charAt(firstLetterIndex);

  // Second letter: 100km squares within the 500km square (5x5 grid, I is omitted)
  // Letters go: VWXYZ, QRSTU, LMNOP, FGHJK, ABCDE (left to right, top to bottom)
  const secondLetterArray = [
    ['V', 'W', 'X', 'Y', 'Z'],  // Row 4 (north)
    ['Q', 'R', 'S', 'T', 'U'],  // Row 3
    ['L', 'M', 'N', 'O', 'P'],  // Row 2
    ['F', 'G', 'H', 'J', 'K'],  // Row 1
    ['A', 'B', 'C', 'D', 'E']   // Row 0 (south)
  ];

  const row = 4 - (n100km % 5);  // Invert because letters go from top (north) to bottom (south)
  const col = e100km % 5;
  const secondLetter = secondLetterArray[row][col];

  // Get numeric part (within 100km square)
  const e = Math.floor(eastings % 100000);
  const n = Math.floor(northings % 100000);

  // Format as 5-digit strings with leading zeros
  const eStr = e.toString().padStart(5, "0");
  const nStr = n.toString().padStart(5, "0");

  return `${firstLetter}${secondLetter} ${eStr} ${nStr}`;
}

/**
 * Convert OSGB36 Eastings/Northings to WGS84 lat/lon
 * Reverse transformation of wgs84ToOSGB
 */
export function osgbToWGS84(eastings: number, northings: number): { lat: number; lon: number } {
  // OSGB36 parameters
  const a_osgb = 6377563.396;
  const b_osgb = 6356256.909;
  const e2_osgb = 1 - (b_osgb * b_osgb) / (a_osgb * a_osgb);

  // National Grid parameters
  const lat0 = (49 * Math.PI) / 180; // True origin latitude
  const lon0 = (-2 * Math.PI) / 180; // True origin longitude
  const N0 = -100000; // Northing of true origin
  const E0 = 400000; // Easting of true origin
  const F0 = 0.9996012717; // Scale factor on central meridian

  const n = (a_osgb - b_osgb) / (a_osgb + b_osgb);
  const n2 = n * n;
  const n3 = n * n * n;

  // Initial estimate of latitude
  let lat = lat0 + (northings - N0) / (a_osgb * F0);

  // Iteratively refine latitude estimate
  for (let i = 0; i < 10; i++) {
    const M =
      b_osgb *
      F0 *
      ((1 + n + (5 / 4) * n2 + (5 / 4) * n3) * (lat - lat0) -
        (3 * n + 3 * n2 + (21 / 8) * n3) * Math.sin(lat - lat0) * Math.cos(lat + lat0) +
        ((15 / 8) * n2 + (15 / 8) * n3) * Math.sin(2 * (lat - lat0)) * Math.cos(2 * (lat + lat0)) -
        ((35 / 24) * n3) * Math.sin(3 * (lat - lat0)) * Math.cos(3 * (lat + lat0)));

    lat = lat + (northings - N0 - M) / (a_osgb * F0);
  }

  const sinLat = Math.sin(lat);
  const cosLat = Math.cos(lat);
  const nu = a_osgb * F0 / Math.sqrt(1 - e2_osgb * sinLat * sinLat);
  const rho = a_osgb * F0 * (1 - e2_osgb) / Math.pow(1 - e2_osgb * sinLat * sinLat, 1.5);
  const eta2 = nu / rho - 1;

  const tanLat = Math.tan(lat);
  const tan2Lat = tanLat * tanLat;
  const tan4Lat = tan2Lat * tan2Lat;
  const tan6Lat = tan4Lat * tan2Lat;

  const VII = tanLat / (2 * rho * nu);
  const VIII = (tanLat / (24 * rho * nu * nu * nu)) * (5 + 3 * tan2Lat + eta2 - 9 * tan2Lat * eta2);
  const IX = (tanLat / (720 * rho * Math.pow(nu, 5))) * (61 + 90 * tan2Lat + 45 * tan4Lat);

  const X = 1 / (cosLat * nu);
  const XI = 1 / (cosLat * 6 * nu * nu * nu) * (nu / rho + 2 * tan2Lat);
  const XII = 1 / (cosLat * 120 * Math.pow(nu, 5)) * (5 + 28 * tan2Lat + 24 * tan4Lat);
  const XIIA = 1 / (cosLat * 5040 * Math.pow(nu, 7)) * (61 + 662 * tan2Lat + 1320 * tan4Lat + 720 * tan6Lat);

  const dE = eastings - E0;
  const dE2 = dE * dE;
  const dE3 = dE2 * dE;
  const dE4 = dE3 * dE;
  const dE5 = dE4 * dE;
  const dE6 = dE5 * dE;
  const dE7 = dE6 * dE;

  const latOsgb = lat - VII * dE2 + VIII * dE4 - IX * dE6;
  const lonOsgb = lon0 + X * dE - XI * dE3 + XII * dE5 - XIIA * dE7;

  // Convert OSGB36 to WGS84 using Helmert transformation
  // OSGB36 parameters
  const a_osgb2 = 6377563.396;
  const b_osgb2 = 6356256.909;
  const e2_osgb2 = 1 - (b_osgb2 * b_osgb2) / (a_osgb2 * a_osgb2);

  // WGS84 parameters
  const a_wgs = 6378137.0;
  const b_wgs = 6356752.314;
  const e2_wgs = 1 - (b_wgs * b_wgs) / (a_wgs * a_wgs);

  // Helmert transformation parameters (OSGB36 to WGS84 - inverse of WGS84 to OSGB36)
  const tx = 446.448; // metres (negated)
  const ty = -125.157;
  const tz = 542.060;
  const rx = 0.1502; // seconds (negated)
  const ry = 0.2470;
  const rz = 0.8421;
  const s = -20.4894; // ppm (negated)

  // Convert OSGB36 lat/lon to Cartesian coordinates
  const nu2 = a_osgb2 / Math.sqrt(1 - e2_osgb2 * Math.sin(latOsgb) * Math.sin(latOsgb));
  const x1 = nu2 * Math.cos(latOsgb) * Math.cos(lonOsgb);
  const y1 = nu2 * Math.cos(latOsgb) * Math.sin(lonOsgb);
  const z1 = (1 - e2_osgb2) * nu2 * Math.sin(latOsgb);

  // Apply Helmert transformation
  const rxRad = (rx / 3600) * (Math.PI / 180);
  const ryRad = (ry / 3600) * (Math.PI / 180);
  const rzRad = (rz / 3600) * (Math.PI / 180);
  const s1 = s / 1e6 + 1;

  const x2 = tx + x1 * s1 - y1 * rzRad + z1 * ryRad;
  const y2 = ty + x1 * rzRad + y1 * s1 - z1 * rxRad;
  const z2 = tz - x1 * ryRad + y1 * rxRad + z1 * s1;

  // Convert Cartesian to WGS84 lat/lon
  const p = Math.sqrt(x2 * x2 + y2 * y2);
  let latWgs = Math.atan2(z2, p * (1 - e2_wgs));

  // Iterate to improve accuracy
  for (let i = 0; i < 10; i++) {
    const nu3 = a_wgs / Math.sqrt(1 - e2_wgs * Math.sin(latWgs) * Math.sin(latWgs));
    latWgs = Math.atan2(z2 + e2_wgs * nu3 * Math.sin(latWgs), p);
  }

  const lonWgs = Math.atan2(y2, x2);

  return {
    lat: (latWgs * 180) / Math.PI,
    lon: (lonWgs * 180) / Math.PI,
  };
}

