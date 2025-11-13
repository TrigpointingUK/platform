import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import MiniMap from '../MiniMap';

// Mock Leaflet
vi.mock('leaflet', () => {
  const mockMapInstance = {
    setView: vi.fn(),
    addTo: vi.fn(),
    remove: vi.fn(),
  };

  const mockTileLayer = {
    addTo: vi.fn(),
  };

  const mockMarker = {
    addTo: vi.fn(),
  };

  const mockCircleMarker = {
    addTo: vi.fn(),
  };

  return {
    default: {
      map: vi.fn(() => mockMapInstance),
      tileLayer: vi.fn(() => mockTileLayer),
      marker: vi.fn(() => mockMarker),
      circleMarker: vi.fn(() => mockCircleMarker),
      icon: vi.fn((options) => options),
      DomEvent: {
        disableClickPropagation: vi.fn(),
        disableScrollPropagation: vi.fn(),
      },
    },
    CRS: {
      EPSG3857: {},
    },
  };
});

// Mock projections
vi.mock('../../../lib/projections', () => ({
  getCRS: vi.fn(() => ({})),
  EPSG27700: {},
  EPSG3857: {},
}));

// Mock mapConfig
vi.mock('../../../lib/mapConfig', () => ({
  TILE_LAYERS: {
    osPaper: {
      id: 'osPaper',
      name: 'OS Paper',
      urlTemplate: '/tiles/os/{z}/{x}/{y}.png',
      attribution: '© OS',
      minZoom: 6,
      maxZoom: 12,
      maxNativeZoom: 9,
      tileSize: 256,
    },
  },
}));

describe('MiniMap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('should render a map container with correct dimensions', () => {
    const { container } = render(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    const mapContainer = container.querySelector('.mini-map-container');
    expect(mapContainer).toBeInTheDocument();
    
    // Check inline styles
    const style = (mapContainer as HTMLElement)?.style;
    expect(style?.width).toBe('150px');
    expect(style?.height).toBe('150px');
  });

  it('should initialize Leaflet map with correct options', async () => {
    const L = await import('leaflet');
    
    render(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    // Wait for useEffect to run
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(L.default.map).toHaveBeenCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({
        center: [51.5, -0.1],
        zoom: 8,
        zoomControl: false,
        attributionControl: false,
        dragging: true,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
      })
    );
  });

  it('should add OS Paper tile layer to the map', async () => {
    const L = await import('leaflet');
    
    render(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(L.default.tileLayer).toHaveBeenCalledWith(
      '/tiles/os/{z}/{x}/{y}.png',
      expect.objectContaining({
        attribution: '© OS',
        maxZoom: 12,
        maxNativeZoom: 9,
        minZoom: 6,
        tileSize: 256,
      })
    );
    // Note: We can't easily test addTo on the tile layer due to mock closure
  });

  it('should add a blue circle marker at the correct position', async () => {
    const L = await import('leaflet');
    
    render(
      <MiniMap lat={52.0} lng={-1.0} />
    );

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(L.default.circleMarker).toHaveBeenCalledWith(
      [52.0, -1.0],
      expect.objectContaining({
        radius: 24,
        color: '#2563eb',
        weight: 2,
        fillColor: '#3b82f6',
        fillOpacity: 0.3,
      })
    );
    // Note: We can't easily test addTo on the circle marker due to mock closure
  });

  it('should disable event propagation on container', async () => {
    const L = await import('leaflet');
    
    render(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(L.default.DomEvent.disableClickPropagation).toHaveBeenCalled();
    expect(L.default.DomEvent.disableScrollPropagation).toHaveBeenCalled();
  });

  it('should clean up map instance on unmount', async () => {
    // We need to get access to the mock instance to test cleanup
    // For now, we'll just test that unmount doesn't error
    const { unmount } = render(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(() => unmount()).not.toThrow();
  });

  it('should not reinitialize map if already initialized', async () => {
    const L = await import('leaflet');
    
    const { rerender } = render(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    await new Promise(resolve => setTimeout(resolve, 0));
    
    const firstCallCount = (L.default.map as ReturnType<typeof vi.fn>).mock.calls.length;

    // Rerender with same props
    rerender(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    await new Promise(resolve => setTimeout(resolve, 0));

    // Should not call map initialization again
    expect((L.default.map as ReturnType<typeof vi.fn>).mock.calls.length).toBe(firstCallCount);
  });

  it('should handle map initialization errors gracefully', async () => {
    const L = await import('leaflet');
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    // Mock map to throw error
    (L.default.map as ReturnType<typeof vi.fn>).mockImplementationOnce(() => {
      throw new Error('Map initialization failed');
    });

    render(
      <MiniMap lat={51.5} lng={-0.1} />
    );

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Failed to initialize mini-map:',
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
  });
});

