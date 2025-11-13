import { describe, it, expect } from 'vitest';
import { getCRS, EPSG3857, EPSG27700 } from '../projections';
import L from 'leaflet';

describe('projections', () => {
  describe('EPSG3857', () => {
    it('should be Web Mercator CRS', () => {
      expect(EPSG3857).toBe(L.CRS.EPSG3857);
    });

    it('should have expected properties', () => {
      expect(EPSG3857).toHaveProperty('code');
      expect(EPSG3857).toHaveProperty('projection');
      expect(EPSG3857).toHaveProperty('transformation');
    });
  });

  describe('EPSG27700', () => {
    it('should be defined as British National Grid', () => {
      expect(EPSG27700).toBeDefined();
    });

    it('should have expected properties', () => {
      expect(EPSG27700).toHaveProperty('code');
      expect(EPSG27700.code).toBe('EPSG:27700');
    });

    it('should have projection defined', () => {
      expect(EPSG27700).toHaveProperty('projection');
      expect(EPSG27700.projection).toBeDefined();
    });

    it('should have transformation defined', () => {
      expect(EPSG27700).toHaveProperty('transformation');
      expect(EPSG27700.transformation).toBeDefined();
    });

    it('should have custom resolutions array', () => {
      expect(EPSG27700.options).toHaveProperty('resolutions');
      const resolutions = EPSG27700.options.resolutions;
      expect(Array.isArray(resolutions)).toBe(true);
      expect(resolutions.length).toBeGreaterThan(0);
    });

    it('should have origin point defined', () => {
      expect(EPSG27700.options).toHaveProperty('origin');
      expect(Array.isArray(EPSG27700.options.origin)).toBe(true);
      expect(EPSG27700.options.origin).toEqual([-238375.0, 1376256.0]);
    });

    it('should have bounds defined for UK', () => {
      expect(EPSG27700.options).toHaveProperty('bounds');
      expect(EPSG27700.options.bounds).toBeDefined();
    });

    it('should have resolutions in descending order', () => {
      const resolutions = EPSG27700.options.resolutions as number[];
      for (let i = 0; i < resolutions.length - 1; i++) {
        expect(resolutions[i]).toBeGreaterThan(resolutions[i + 1]);
      }
    });
  });

  describe('getCRS', () => {
    it('should return EPSG3857 by default', () => {
      const crs = getCRS('');
      expect(crs).toBe(EPSG3857);
    });

    it('should return EPSG3857 for explicit string', () => {
      const crs = getCRS('EPSG:3857');
      expect(crs).toBe(EPSG3857);
    });

    it('should return EPSG27700 when requested', () => {
      const crs = getCRS('EPSG:27700');
      expect(crs).toBe(EPSG27700);
    });

    it('should return EPSG3857 for unknown identifier', () => {
      const crs = getCRS('EPSG:4326');
      expect(crs).toBe(EPSG3857);
    });

    it('should return EPSG3857 for invalid input', () => {
      const crs = getCRS('invalid');
      expect(crs).toBe(EPSG3857);
    });

    it('should be case-sensitive', () => {
      // Expect case-sensitive matching
      const crs = getCRS('epsg:27700');
      expect(crs).toBe(EPSG3857); // Falls back to default
    });
  });

  describe('CRS compatibility', () => {
    it('should support standard Web Mercator projections', () => {
      const crs = getCRS('EPSG:3857');
      expect(crs).toBeDefined();
      expect(crs.code).toContain('3857');
    });

    it('should support British National Grid projections', () => {
      const crs = getCRS('EPSG:27700');
      expect(crs).toBeDefined();
      expect(crs.code).toBe('EPSG:27700');
    });
  });

  describe('TrigDetailMap CRS requirements', () => {
    it('should provide correct CRS for OSM tiles', () => {
      // OSM uses EPSG:3857
      const crs = getCRS('EPSG:3857');
      expect(crs).toBe(L.CRS.EPSG3857);
    });

    it('should provide correct CRS for OS Paper tiles', () => {
      // OS Paper uses EPSG:27700
      const crs = getCRS('EPSG:27700');
      expect(crs.code).toBe('EPSG:27700');
    });

    it('should have all required methods for Leaflet', () => {
      const crs = getCRS('EPSG:27700');
      expect(typeof crs.latLngToPoint).toBe('function');
      expect(typeof crs.pointToLatLng).toBe('function');
      expect(typeof crs.project).toBe('function');
      expect(typeof crs.unproject).toBe('function');
      expect(typeof crs.scale).toBe('function');
      expect(typeof crs.zoom).toBe('function');
    });
  });

  describe('Projection stability', () => {
    it('should maintain stable EPSG:3857 code', () => {
      expect(EPSG3857.code).toContain('3857');
    });

    it('should maintain stable EPSG:27700 code', () => {
      expect(EPSG27700.code).toBe('EPSG:27700');
    });

    it('should return consistent CRS instances', () => {
      const crs1 = getCRS('EPSG:3857');
      const crs2 = getCRS('EPSG:3857');
      expect(crs1).toBe(crs2);
    });

    it('should return consistent EPSG27700 instances', () => {
      const crs1 = getCRS('EPSG:27700');
      const crs2 = getCRS('EPSG:27700');
      expect(crs1).toBe(crs2);
    });
  });
});

