import { describe, it, expect } from 'vitest';
import { calculateBearing, calculateDistance, wgs84ToOSGB, osgbToWGS84 } from '../coordinates';

describe('calculateBearing', () => {
  it('should return 0 for due north', () => {
    // Start at 51.5, -0.12, end at 51.6, -0.12 (north)
    const bearing = calculateBearing(51.5, -0.12, 51.6, -0.12);
    expect(bearing).toBeCloseTo(0, 1);
  });

  it('should return 90 for due east', () => {
    // Start at 51.5, -0.12, end at 51.5, 0.0 (east)
    const bearing = calculateBearing(51.5, -0.12, 51.5, 0.0);
    expect(bearing).toBeCloseTo(90, 0);
  });

  it('should return 180 for due south', () => {
    // Start at 51.5, -0.12, end at 51.4, -0.12 (south)
    const bearing = calculateBearing(51.5, -0.12, 51.4, -0.12);
    expect(bearing).toBeCloseTo(180, 1);
  });

  it('should return 270 for due west', () => {
    // Start at 51.5, -0.12, end at 51.5, -0.24 (west)
    const bearing = calculateBearing(51.5, -0.12, 51.5, -0.24);
    expect(bearing).toBeCloseTo(270, 0);
  });

  it('should return approximately 45 for northeast', () => {
    // Northeast bearing
    const bearing = calculateBearing(51.5, -0.12, 51.6, 0.0);
    expect(bearing).toBeGreaterThan(30);
    expect(bearing).toBeLessThan(60);
  });

  it('should return approximately 135 for southeast', () => {
    const bearing = calculateBearing(51.5, -0.12, 51.4, 0.0);
    expect(bearing).toBeGreaterThan(120);
    expect(bearing).toBeLessThan(150);
  });

  it('should return approximately 225 for southwest', () => {
    const bearing = calculateBearing(51.5, -0.12, 51.4, -0.24);
    expect(bearing).toBeGreaterThan(210);
    expect(bearing).toBeLessThan(240);
  });

  it('should return approximately 315 for northwest', () => {
    const bearing = calculateBearing(51.5, -0.12, 51.6, -0.24);
    expect(bearing).toBeGreaterThan(300);
    expect(bearing).toBeLessThan(330);
  });

  it('should always return a value between 0 and 360', () => {
    const testCases = [
      [51.5, -0.12, 51.6, -0.12],
      [51.5, -0.12, 51.5, 0.0],
      [51.5, -0.12, 51.4, -0.12],
      [51.5, -0.12, 51.5, -0.24],
      [52.0, -1.0, 53.0, 1.0],
      [-33.9, 151.2, 35.7, 139.7], // Sydney to Tokyo
    ];

    testCases.forEach(([lat1, lon1, lat2, lon2]) => {
      const bearing = calculateBearing(lat1, lon1, lat2, lon2);
      expect(bearing).toBeGreaterThanOrEqual(0);
      expect(bearing).toBeLessThan(360);
    });
  });

  it('should handle same point (undefined bearing)', () => {
    // When start and end points are the same, bearing is technically undefined
    // but our implementation should return a valid number
    const bearing = calculateBearing(51.5, -0.12, 51.5, -0.12);
    expect(typeof bearing).toBe('number');
    expect(!isNaN(bearing)).toBe(true);
  });

  it('should handle equatorial points', () => {
    const bearing = calculateBearing(0, 0, 0, 1);
    expect(bearing).toBeCloseTo(90, 0);
  });

  it('should handle polar regions', () => {
    // High latitude point
    const bearing = calculateBearing(85, 0, 85, 10);
    expect(bearing).toBeGreaterThan(0);
    expect(bearing).toBeLessThan(360);
  });
});

describe('calculateDistance', () => {
  it('should return 0 for the same point', () => {
    const distance = calculateDistance(51.5, -0.12, 51.5, -0.12);
    expect(distance).toBe(0);
  });

  it('should calculate approximately 111km for 1 degree latitude change', () => {
    // 1 degree of latitude is approximately 111km
    const distance = calculateDistance(51.0, -0.12, 52.0, -0.12);
    expect(distance).toBeGreaterThan(110000);
    expect(distance).toBeLessThan(112000);
  });

  it('should calculate approximately 11m for 0.0001 degree latitude change', () => {
    // 0.0001 degree of latitude is approximately 11m
    const distance = calculateDistance(51.5000, -0.12, 51.5001, -0.12);
    expect(distance).toBeGreaterThan(10);
    expect(distance).toBeLessThan(12);
  });

  it('should be symmetric', () => {
    const d1 = calculateDistance(51.5, -0.12, 52.0, 0.0);
    const d2 = calculateDistance(52.0, 0.0, 51.5, -0.12);
    expect(d1).toBeCloseTo(d2, 5);
  });

  it('should handle long distances', () => {
    // London to New York is approximately 5570km
    const distance = calculateDistance(51.5, -0.12, 40.7, -74.0);
    expect(distance).toBeGreaterThan(5500000);
    expect(distance).toBeLessThan(5600000);
  });

  it('should handle equatorial points', () => {
    // 1 degree of longitude at the equator is approximately 111km
    const distance = calculateDistance(0, 0, 0, 1);
    expect(distance).toBeGreaterThan(110000);
    expect(distance).toBeLessThan(112000);
  });

  it('should handle small distances (typical for moved trigs)', () => {
    // ~10m movement - typical for a moved trig
    const distance = calculateDistance(51.50000, -0.12000, 51.50009, -0.12000);
    expect(distance).toBeGreaterThan(5);
    expect(distance).toBeLessThan(15);
  });

  it('should handle 100m distance (larger trig movement)', () => {
    // ~100m movement
    const distance = calculateDistance(51.50000, -0.12000, 51.50090, -0.12000);
    expect(distance).toBeGreaterThan(95);
    expect(distance).toBeLessThan(105);
  });
});

describe('wgs84ToOSGB', () => {
  it('should return valid eastings and northings for London', () => {
    // Approximate Big Ben coordinates
    const result = wgs84ToOSGB(51.5007, -0.1246);
    
    // Should have valid eastings and northings
    expect(result.eastings).toBeGreaterThan(0);
    expect(result.northings).toBeGreaterThan(0);
  });

  it('should return valid grid reference format', () => {
    // Approximate Newcastle coordinates
    const result = wgs84ToOSGB(54.9783, -1.6178);
    
    // Should be in valid format (2 letters, space, 5 digits, space, 5 digits)
    expect(result.gridRef).toMatch(/^[A-Z]{2} \d{5} \d{5}$/);
  });

  it('should return valid grid reference for Scotland', () => {
    // Approximate Edinburgh coordinates
    const result = wgs84ToOSGB(55.9533, -3.1883);
    
    // Should be in valid format
    expect(result.gridRef).toMatch(/^[A-Z]{2} \d{5} \d{5}$/);
  });

  it('should format grid reference correctly', () => {
    const result = wgs84ToOSGB(51.5, -0.12);
    
    // Grid reference should be in format "XX 00000 00000"
    expect(result.gridRef).toMatch(/^[A-Z]{2} \d{5} \d{5}$/);
  });

  it('should return consistent eastings/northings with grid reference', () => {
    const result = wgs84ToOSGB(51.5, -0.12);
    
    // The grid reference should encode the eastings/northings
    const parts = result.gridRef.split(' ');
    const gridE = parseInt(parts[1], 10);
    const gridN = parseInt(parts[2], 10);
    
    // The numeric parts should match the last 5 digits of eastings/northings
    expect(gridE).toBe(Math.floor(result.eastings % 100000));
    expect(gridN).toBe(Math.floor(result.northings % 100000));
  });
});

describe('osgbToWGS84', () => {
  it('should convert central London eastings/northings correctly', () => {
    // TQ 30000 80000 is approximately Westminster
    const result = osgbToWGS84(530000, 180000);
    
    // Should be near London
    expect(result.lat).toBeGreaterThan(51.4);
    expect(result.lat).toBeLessThan(51.6);
    expect(result.lon).toBeGreaterThan(-0.2);
    expect(result.lon).toBeLessThan(0.0);
  });

  it('should be roughly inverse of wgs84ToOSGB', () => {
    const originalLat = 51.5;
    const originalLon = -0.12;
    
    // Convert to OSGB
    const osgb = wgs84ToOSGB(originalLat, originalLon);
    
    // Convert back to WGS84
    const wgs84 = osgbToWGS84(osgb.eastings, osgb.northings);
    
    // Should be close to original (within ~1m accuracy)
    expect(wgs84.lat).toBeCloseTo(originalLat, 4);
    expect(wgs84.lon).toBeCloseTo(originalLon, 4);
  });

  it('should handle various GB locations', () => {
    const testCases = [
      { e: 530000, n: 180000 }, // London
      { e: 425000, n: 564000 }, // Newcastle
      { e: 327000, n: 673000 }, // Edinburgh
      { e: 318000, n: 175000 }, // Bristol
      { e: 385000, n: 339000 }, // Birmingham
    ];

    testCases.forEach(({ e, n }) => {
      const result = osgbToWGS84(e, n);
      
      // All results should be within GB
      expect(result.lat).toBeGreaterThan(49);
      expect(result.lat).toBeLessThan(61);
      expect(result.lon).toBeGreaterThan(-8);
      expect(result.lon).toBeLessThan(2);
    });
  });
});

describe('integration: bearing and distance for moved trig scenario', () => {
  it('should correctly calculate bearing and distance for a typical moved trig', () => {
    // Scenario: trig moved ~50m northeast
    const currentLat = 51.50030;
    const currentLon = -0.11970;
    const originalLat = 51.50000;
    const originalLon = -0.12000;

    const distance = calculateDistance(currentLat, currentLon, originalLat, originalLon);
    const bearing = calculateBearing(currentLat, currentLon, originalLat, originalLon);

    // Distance should be approximately 40-60m
    expect(distance).toBeGreaterThan(35);
    expect(distance).toBeLessThan(60);

    // Bearing should be roughly southwest (since original is south-west of current)
    expect(bearing).toBeGreaterThan(180);
    expect(bearing).toBeLessThan(270);
  });

  it('should handle a trig moved due east', () => {
    const currentLat = 51.5;
    const currentLon = -0.10; // moved east
    const originalLat = 51.5;
    const originalLon = -0.12;

    const bearing = calculateBearing(currentLat, currentLon, originalLat, originalLon);
    
    // Bearing from current to original should be west (270)
    expect(bearing).toBeCloseTo(270, 0);
  });

  it('should handle a trig moved due north', () => {
    const currentLat = 51.52; // moved north
    const currentLon = -0.12;
    const originalLat = 51.50;
    const originalLon = -0.12;

    const bearing = calculateBearing(currentLat, currentLon, originalLat, originalLon);
    
    // Bearing from current to original should be south (180)
    expect(bearing).toBeCloseTo(180, 0);
  });
});

