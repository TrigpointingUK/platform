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
};

/**
 * Trigpoints with different conditions for testing color modes
 */
export const trigsByCondition = {
  good: createMockTrig({ id: 1, condition: 'G', name: 'Good Trig' }),
  damaged: createMockTrig({ id: 2, condition: 'D', name: 'Damaged Trig' }),
  missing: createMockTrig({ id: 3, condition: 'M', name: 'Missing Trig' }),
  possibly: createMockTrig({ id: 4, condition: 'P', name: 'Possibly Missing Trig' }),
  unknown: createMockTrig({ id: 5, condition: 'U', name: 'Unknown Trig' }),
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

