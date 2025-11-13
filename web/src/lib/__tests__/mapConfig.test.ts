import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  getTileLayer,
  getAvailableTileLayers,
  getPreferredTileLayer,
  setPreferredTileLayer,
  MAP_CONFIG,
  DEFAULT_TILE_LAYER,
  TILE_LAYER_STORAGE_KEY,
  TILE_LAYERS,
} from '../mapConfig';
import { mockLocalStorage } from '../../components/map/__tests__/test-utils';

describe('mapConfig', () => {
  describe('getTileLayer', () => {
    it('should return correct layer by ID', () => {
      const layer = getTileLayer('osm');
      expect(layer).toBeDefined();
      expect(layer.id).toBe('osm');
      expect(layer.name).toBe('OpenStreetMap');
    });

    it('should return correct layer for osDigital', () => {
      const layer = getTileLayer('osDigital');
      expect(layer).toBeDefined();
      expect(layer.id).toBe('osDigital');
      expect(layer.crs).toBe('EPSG:3857');
    });

    it('should return correct layer for osPaper (EPSG:27700)', () => {
      const layer = getTileLayer('osPaper');
      expect(layer).toBeDefined();
      expect(layer.id).toBe('osPaper');
      expect(layer.crs).toBe('EPSG:27700');
    });

    it('should fall back to default for invalid ID', () => {
      const layer = getTileLayer('invalid-layer-id');
      expect(layer).toBeDefined();
      expect(layer.id).toBe(DEFAULT_TILE_LAYER);
    });

    it('should fall back to default for empty string', () => {
      const layer = getTileLayer('');
      expect(layer).toBeDefined();
      expect(layer.id).toBe(DEFAULT_TILE_LAYER);
    });
  });

  describe('getAvailableTileLayers', () => {
    it('should return array of all layers', () => {
      const layers = getAvailableTileLayers();
      expect(Array.isArray(layers)).toBe(true);
      expect(layers.length).toBeGreaterThan(0);
    });

    it('should return layers with required properties', () => {
      const layers = getAvailableTileLayers();
      layers.forEach(layer => {
        expect(layer).toHaveProperty('id');
        expect(layer).toHaveProperty('name');
        expect(layer).toHaveProperty('urlTemplate');
        expect(layer).toHaveProperty('attribution');
        expect(layer).toHaveProperty('maxZoom');
      });
    });

    it('should include OSM layer', () => {
      const layers = getAvailableTileLayers();
      const osmLayer = layers.find(l => l.id === 'osm');
      expect(osmLayer).toBeDefined();
      expect(osmLayer?.name).toBe('OpenStreetMap');
    });

    it('should include layers with different CRS', () => {
      const layers = getAvailableTileLayers();
      const has3857 = layers.some(l => l.crs === 'EPSG:3857' || !l.crs);
      const has27700 = layers.some(l => l.crs === 'EPSG:27700');
      expect(has3857).toBe(true);
      expect(has27700).toBe(true);
    });
  });

  describe('localStorage preferences', () => {
    let localStorageMock: ReturnType<typeof mockLocalStorage>;

    beforeEach(() => {
      localStorageMock = mockLocalStorage();
    });

    afterEach(() => {
      localStorageMock.localStorageMock.clear();
    });

    describe('getPreferredTileLayer', () => {
      it('should return default when no preference stored', () => {
        const preferred = getPreferredTileLayer();
        expect(preferred).toBe(DEFAULT_TILE_LAYER);
      });

      it('should return stored preference', () => {
        localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osDigital');
        const preferred = getPreferredTileLayer();
        expect(preferred).toBe('osDigital');
      });

      it('should handle localStorage errors gracefully', () => {
        localStorageMock.localStorageMock.getItem.mockImplementation(() => {
          throw new Error('localStorage error');
        });
        const preferred = getPreferredTileLayer();
        expect(preferred).toBe(DEFAULT_TILE_LAYER);
      });
    });

    describe('setPreferredTileLayer', () => {
      it('should save preference to localStorage', () => {
        setPreferredTileLayer('osDigital');
        expect(localStorageMock.localStorageMock.setItem).toHaveBeenCalledWith(
          TILE_LAYER_STORAGE_KEY,
          'osDigital'
        );
      });

      it('should handle localStorage errors gracefully', () => {
        localStorageMock.localStorageMock.setItem.mockImplementation(() => {
          throw new Error('localStorage error');
        });
        expect(() => setPreferredTileLayer('osDigital')).not.toThrow();
      });
    });

    it('should persist and retrieve tile layer preference', () => {
      setPreferredTileLayer('osPaper');
      const retrieved = getPreferredTileLayer();
      expect(retrieved).toBe('osPaper');
    });
  });

  describe('MAP_CONFIG constants', () => {
    it('should have stable default center', () => {
      expect(MAP_CONFIG.defaultCenter).toEqual({ lat: 54.5, lng: -2.0 });
    });

    it('should have stable default zoom', () => {
      expect(MAP_CONFIG.defaultZoom).toBe(6);
    });

    it('should have stable zoom limits', () => {
      expect(MAP_CONFIG.minZoom).toBe(4);
      expect(MAP_CONFIG.maxZoom).toBe(20);
    });

    it('should have stable detail map settings', () => {
      expect(MAP_CONFIG.detailMapZoom).toBe(14);
      expect(MAP_CONFIG.detailMapHeight).toBe(350);
    });

    it('should have stable marker threshold', () => {
      expect(MAP_CONFIG.markerThreshold).toBe(500);
    });

    it('should have stable viewport padding', () => {
      expect(MAP_CONFIG.viewportPadding).toBe(0.1);
    });

    it('should have stable debounce setting', () => {
      expect(MAP_CONFIG.debounceMs).toBe(500);
    });
  });

  describe('TILE_LAYERS structure', () => {
    it('should have OSM layer defined', () => {
      expect(TILE_LAYERS.osm).toBeDefined();
      expect(TILE_LAYERS.osm.crs).toBe('EPSG:3857');
    });

    it('should have OS Digital layer defined', () => {
      expect(TILE_LAYERS.osDigital).toBeDefined();
      expect(TILE_LAYERS.osDigital.crs).toBe('EPSG:3857');
    });

    it('should have OS Paper layer with British National Grid', () => {
      expect(TILE_LAYERS.osPaper).toBeDefined();
      expect(TILE_LAYERS.osPaper.crs).toBe('EPSG:27700');
    });

    it('should have zoom limits for each layer', () => {
      Object.values(TILE_LAYERS).forEach(layer => {
        expect(typeof layer.minZoom).toBe('number');
        expect(typeof layer.maxZoom).toBe('number');
        expect(layer.minZoom).toBeLessThan(layer.maxZoom);
      });
    });

    it('should have valid maxNativeZoom when specified', () => {
      Object.values(TILE_LAYERS).forEach(layer => {
        if (layer.maxNativeZoom !== undefined) {
          expect(layer.maxNativeZoom).toBeLessThanOrEqual(layer.maxZoom);
        }
      });
    });
  });

  describe('Tile layer compatibility with TrigDetailMap', () => {
    it('should support EPSG:3857 tiles for standard zoom levels', () => {
      const layer = getTileLayer('osm');
      expect(layer.crs).toBe('EPSG:3857');
      expect(MAP_CONFIG.detailMapZoom).toBeGreaterThanOrEqual(layer.minZoom || 0);
      expect(MAP_CONFIG.detailMapZoom).toBeLessThanOrEqual(layer.maxZoom);
    });

    it('should support EPSG:27700 tiles with adjusted zoom levels', () => {
      const layer = getTileLayer('osPaper');
      expect(layer.crs).toBe('EPSG:27700');
      // TrigDetailMap adjusts zoom to 8 for EPSG:27700
      expect(8).toBeGreaterThanOrEqual(layer.minZoom || 0);
      expect(8).toBeLessThanOrEqual(layer.maxZoom);
    });
  });
});

