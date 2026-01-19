/**
 * Testing utilities for map components
 * 
 * Provides mocks, fixtures, and helper functions for testing Leaflet-based components.
 */

import { vi } from 'vitest';
import type { Map as LeafletMap } from 'leaflet';
import type { TrigData } from '../types';

/**
 * Mock Leaflet map instance
 */
export const createMockMap = (): Partial<LeafletMap> => ({
  setView: vi.fn().mockReturnThis(),
  getZoom: vi.fn().mockReturnValue(7),
  setZoom: vi.fn().mockReturnThis(),
  getBounds: vi.fn().mockReturnValue({
    getNorth: () => 55,
    getSouth: () => 50,
    getEast: () => 0,
    getWest: () => -5,
  }),
  setMinZoom: vi.fn().mockReturnThis(),
  setMaxZoom: vi.fn().mockReturnThis(),
  invalidateSize: vi.fn().mockReturnThis(),
  on: vi.fn().mockReturnThis(),
  off: vi.fn().mockReturnThis(),
  remove: vi.fn().mockReturnThis(),
});

/**
 * Mock geolocation API
 */
export const mockGeolocation = () => {
  const getCurrentPositionMock = vi.fn();
  
  Object.defineProperty(globalThis.navigator, 'geolocation', {
    value: {
      getCurrentPosition: getCurrentPositionMock,
      watchPosition: vi.fn(),
      clearWatch: vi.fn(),
    },
    configurable: true,
  });
  
  return { getCurrentPositionMock };
};

/**
 * Mock successful geolocation response
 */
export const mockGeolocationSuccess = (lat: number, lon: number) => {
  const { getCurrentPositionMock } = mockGeolocation();
  
  getCurrentPositionMock.mockImplementation((success) => {
    success({
      coords: {
        latitude: lat,
        longitude: lon,
        accuracy: 10,
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null,
      },
      timestamp: Date.now(),
    });
  });
  
  return { getCurrentPositionMock };
};

/**
 * Mock geolocation error
 */
export const mockGeolocationError = (code: number = 1) => {
  const { getCurrentPositionMock } = mockGeolocation();
  
  getCurrentPositionMock.mockImplementation((_, error) => {
    error({
      code,
      message: 'Geolocation error',
      PERMISSION_DENIED: 1,
      POSITION_UNAVAILABLE: 2,
      TIMEOUT: 3,
    });
  });
  
  return { getCurrentPositionMock };
};

/**
 * Sample trigpoint data for testing
 */
export const createMockTrig = (overrides?: Partial<TrigData>): TrigData => ({
  id: 1,
  waypoint: 'TP1234',
  name: 'Test Trig Point',
  physical_type: 'Pillar',
  condition: 'G',
  wgs_lat: 51.5074,
  wgs_long: -0.1278,
  osgb_gridref: 'TQ 30 80',
  grid_system: 'gb',  // Default to GB grid
  ...overrides,
});

/**
 * Create a mock Irish trig for testing Irish Grid behaviour
 */
export const createMockIrishTrig = (overrides?: Partial<TrigData>): TrigData => ({
  id: 100,
  waypoint: 'TP5000',
  name: 'Dublin Test Trig',
  physical_type: 'Pillar',
  condition: 'G',
  wgs_lat: 53.3498,
  wgs_long: -6.2603,
  osgb_gridref: 'O 15 34',  // Irish Grid reference format
  grid_system: 'ie',  // Irish Grid
  country_name: 'Ireland',
  ...overrides,
});

/**
 * Create multiple mock trigpoints
 */
export const createMockTrigs = (count: number): TrigData[] => {
  return Array.from({ length: count }, (_, i) => createMockTrig({
    id: i + 1,
    waypoint: `TP${(i + 1).toString().padStart(4, '0')}`,
    name: `Test Trig ${i + 1}`,
    wgs_lat: 51.5 + (i * 0.01),
    wgs_long: -0.1 + (i * 0.01),
  }));
};

/**
 * Mock localStorage
 */
export const mockLocalStorage = () => {
  const store: Record<string, string> = {};
  
  const localStorageMock = {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      Object.keys(store).forEach(key => delete store[key]);
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    }),
  };
  
  Object.defineProperty(globalThis, 'localStorage', {
    value: localStorageMock,
    configurable: true,
    writable: true,
  });
  
  return { store, localStorageMock };
};

/**
 * Mock tile layer configurations for testing
 */
export const mockTileLayers = {
  osm: {
    id: 'osm',
    name: 'OpenStreetMap',
    urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '© OpenStreetMap contributors',
    minZoom: 0,
    maxZoom: 20,
    maxNativeZoom: 19,
    crs: 'EPSG:3857',
    subdomains: ['a', 'b', 'c'],
  },
  osPaper: {
    id: 'osPaper',
    name: 'OS Paper',
    urlTemplate: '/tiles/os/Leisure_27700/{z}/{x}/{y}.png',
    attribution: '© Ordnance Survey',
    minZoom: 6,
    maxZoom: 12,
    maxNativeZoom: 9,
    crs: 'EPSG:27700',
    tileSize: 256,
  },
  openTopoMap: {
    id: 'openTopoMap',
    name: 'OpenTopoMap',
    urlTemplate: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '© OpenTopoMap contributors',
    minZoom: 0,
    maxZoom: 20,
    maxNativeZoom: 17,
    crs: 'EPSG:3857',
    subdomains: ['a', 'b', 'c'],
  },
};

/**
 * Trigpoints with different conditions for testing color modes
 * Based on api/utils/condition_mapping.py:
 * - GREEN: G (Good), S (Slightly damaged)
 * - YELLOW: C, D, R, T, M (Moved), V
 * - RED: Q (Possibly missing), X (Destroyed), N
 * - GREY: P (Inaccessible), U (Unknown), Z
 */
export const trigsByCondition = {
  good: createMockTrig({ id: 1, condition: 'G', name: 'Good Trig' }),
  damaged: createMockTrig({ id: 2, condition: 'D', name: 'Damaged Trig' }),
  moved: createMockTrig({ id: 3, condition: 'M', name: 'Moved Trig' }),
  possiblyMissing: createMockTrig({ id: 4, condition: 'Q', name: 'Possibly Missing Trig' }),
  destroyed: createMockTrig({ id: 5, condition: 'X', name: 'Destroyed Trig' }),
  inaccessible: createMockTrig({ id: 6, condition: 'P', name: 'Inaccessible Trig' }),
  unknown: createMockTrig({ id: 7, condition: 'U', name: 'Unknown Trig' }),
};

/**
 * Trigpoints with different physical types
 */
export const trigsByPhysicalType = {
  pillar: createMockTrig({ id: 1, physical_type: 'Pillar', name: 'Pillar Trig' }),
  fbm: createMockTrig({ id: 2, physical_type: 'FBM', name: 'FBM Trig' }),
  passive: createMockTrig({ id: 3, physical_type: 'Passive Station', name: 'Passive Trig' }),
  intersection: createMockTrig({ id: 4, physical_type: 'Intersection', name: 'Intersection Trig' }),
  bolt: createMockTrig({ id: 5, physical_type: 'Bolt', name: 'Bolt Trig' }),
  active: createMockTrig({ id: 6, physical_type: 'Active Station', name: 'Active Trig' }),
  other: createMockTrig({ id: 7, physical_type: 'Other', name: 'Other Trig' }),
};

/**
 * Clean up mocks after tests
 */
export const cleanupMocks = () => {
  vi.clearAllMocks();
  if (globalThis.localStorage) {
    localStorage.clear();
  }
};

