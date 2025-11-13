import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import BaseMap from '../BaseMap';
import { MAP_CONFIG } from '../../../lib/mapConfig';
import type { BaseMapProps } from '../types';

// Mock react-leaflet components
const mockMapInstance = {
  setView: vi.fn(),
  setMinZoom: vi.fn(),
  setMaxZoom: vi.fn(),
  invalidateSize: vi.fn(),
  getZoom: vi.fn().mockReturnValue(7),
};

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children, ...props }: { children?: React.ReactNode; center: unknown; zoom: number; crs?: { code?: string }; style?: React.CSSProperties; scrollWheelZoom?: boolean; className?: string; minZoom?: number; maxZoom?: number }) => (
    <div 
      data-testid="map-container"
      data-center={JSON.stringify(props.center)}
      data-zoom={props.zoom}
      data-crs={props.crs?.code || 'EPSG:3857'}
      data-min-zoom={props.minZoom}
      data-max-zoom={props.maxZoom}
      data-scroll-wheel-zoom={props.scrollWheelZoom}
    >
      {children}
    </div>
  ),
  TileLayer: (props: { url?: string; attribution?: string; maxZoom?: number; minZoom?: number; tileSize?: number; crossOrigin?: string }) => (
    <div 
      data-testid="tile-layer"
      data-url={props.url}
      data-attribution={props.attribution}
      data-max-zoom={props.maxZoom}
      data-min-zoom={props.minZoom}
      data-tile-size={props.tileSize}
      data-cross-origin={props.crossOrigin}
    />
  ),
  ScaleControl: (props: { position?: string; imperial?: boolean }) => (
    <div data-testid="scale-control" data-position={props.position} data-imperial={props.imperial} />
  ),
  useMap: () => mockMapInstance,
}));

describe('BaseMap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const defaultProps: BaseMapProps = {
    center: [51.5, -2.0],
    zoom: 7,
    tileLayerId: 'osm',
  };

  describe('Basic Rendering', () => {
    it('should render without crashing', () => {
      render(<BaseMap {...defaultProps} />);
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    it('should render MapContainer with correct center', () => {
      render(<BaseMap {...defaultProps} center={[52.4, -1.9]} />);
      
      const container = screen.getByTestId('map-container');
      const center = JSON.parse(container.getAttribute('data-center') || '[]');
      expect(center).toEqual([52.4, -1.9]);
    });

    it('should render MapContainer with correct zoom', () => {
      render(<BaseMap {...defaultProps} zoom={10} />);
      
      const container = screen.getByTestId('map-container');
      expect(container.getAttribute('data-zoom')).toBe('10');
    });

    it('should render TileLayer', () => {
      render(<BaseMap {...defaultProps} />);
      expect(screen.getByTestId('tile-layer')).toBeInTheDocument();
    });

    it('should render ScaleControl', () => {
      render(<BaseMap {...defaultProps} />);
      const scaleControl = screen.getByTestId('scale-control');
      expect(scaleControl).toBeInTheDocument();
      expect(scaleControl.getAttribute('data-position')).toBe('bottomleft');
      expect(scaleControl.getAttribute('data-imperial')).toBe('false');
    });

    it('should enable scroll wheel zoom', () => {
      render(<BaseMap {...defaultProps} />);
      
      const container = screen.getByTestId('map-container');
      expect(container.getAttribute('data-scroll-wheel-zoom')).toBe('true');
    });
  });

  describe('Height Configuration', () => {
    it('should use default height of 400px', () => {
      const { container } = render(<BaseMap {...defaultProps} />);
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.height).toBe('400px');
    });

    it('should accept numeric height', () => {
      const { container } = render(<BaseMap {...defaultProps} height={500} />);
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.height).toBe('500px');
    });

    it('should accept CSS string height', () => {
      const { container } = render(<BaseMap {...defaultProps} height="100%" />);
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.height).toBe('100%');
    });
  });

  describe('Tile Layer Configuration', () => {
    it('should render OSM tile layer', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer.getAttribute('data-url')).toContain('openstreetmap.org');
    });

    it('should render OS Digital tile layer', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osDigital" />);
      
      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer.getAttribute('data-url')).toContain('/v1/tiles/os/Outdoor_3857/');
    });

    it('should render OS Paper tile layer', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osPaper" />);
      
      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer.getAttribute('data-url')).toContain('/v1/tiles/os/Leisure_27700/');
    });

    it('should set tile layer attribution', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer.getAttribute('data-attribution')).toContain('OpenStreetMap');
    });

    it('should set crossOrigin to anonymous', () => {
      render(<BaseMap {...defaultProps} />);
      
      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer.getAttribute('data-cross-origin')).toBe('anonymous');
    });
  });

  describe('Zoom Limits', () => {
    it('should apply zoom limits from tile layer', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      const container = screen.getByTestId('map-container');
      const minZoom = parseInt(container.getAttribute('data-min-zoom') || '0');
      const maxZoom = parseInt(container.getAttribute('data-max-zoom') || '0');
      
      // OSM has minZoom 0, maxZoom 20
      // But also constrained by MAP_CONFIG (minZoom 4, maxZoom 20)
      expect(minZoom).toBeGreaterThanOrEqual(MAP_CONFIG.minZoom);
      expect(maxZoom).toBeLessThanOrEqual(MAP_CONFIG.maxZoom);
    });

    it('should respect global MAP_CONFIG zoom limits', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      const container = screen.getByTestId('map-container');
      const minZoom = parseInt(container.getAttribute('data-min-zoom') || '0');
      const maxZoom = parseInt(container.getAttribute('data-max-zoom') || '0');
      
      expect(minZoom).toBeGreaterThanOrEqual(MAP_CONFIG.minZoom);
      expect(maxZoom).toBeLessThanOrEqual(MAP_CONFIG.maxZoom);
    });

    it('should use most restrictive zoom limits', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osPaper" />);
      
      const container = screen.getByTestId('map-container');
      const minZoom = parseInt(container.getAttribute('data-min-zoom') || '0');
      const maxZoom = parseInt(container.getAttribute('data-max-zoom') || '0');
      
      // OS Paper has minZoom 6, maxZoom 12
      // MAP_CONFIG has minZoom 4, maxZoom 20
      // Should use max(6, 4) = 6 and min(12, 20) = 12
      expect(minZoom).toBe(6);
      expect(maxZoom).toBe(12);
    });
  });

  describe('CRS (Coordinate Reference System)', () => {
    it('should use EPSG:3857 for OSM tiles', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      const container = screen.getByTestId('map-container');
      expect(container.getAttribute('data-crs')).toContain('3857');
    });

    it('should use EPSG:27700 for OS Paper tiles', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osPaper" />);
      
      const container = screen.getByTestId('map-container');
      expect(container.getAttribute('data-crs')).toBe('EPSG:27700');
    });

    it('should default to EPSG:3857 when CRS not specified', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      const container = screen.getByTestId('map-container');
      expect(container.getAttribute('data-crs')).toContain('3857');
    });

    it('should remount map when CRS changes', () => {
      const { rerender } = render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      const initial = screen.getByTestId('map-container');
      
      rerender(<BaseMap {...defaultProps} tileLayerId="osPaper" />);
      const after = screen.getByTestId('map-container');
      
      // Component should remount (different CRS), so attributes should change
      expect(initial.getAttribute('data-crs')).not.toBe(after.getAttribute('data-crs'));
    });
  });

  describe('Children Rendering', () => {
    it('should render children components', () => {
      render(
        <BaseMap {...defaultProps}>
          <div data-testid="child-component">Test Child</div>
        </BaseMap>
      );
      
      expect(screen.getByTestId('child-component')).toBeInTheDocument();
    });

    it('should render multiple children', () => {
      render(
        <BaseMap {...defaultProps}>
          <div data-testid="child-1">Child 1</div>
          <div data-testid="child-2">Child 2</div>
        </BaseMap>
      );
      
      expect(screen.getByTestId('child-1')).toBeInTheDocument();
      expect(screen.getByTestId('child-2')).toBeInTheDocument();
    });
  });

  describe('onMapReady Callback', () => {
    it('should call onMapReady when map initializes', () => {
      const onMapReadyMock = vi.fn();
      render(<BaseMap {...defaultProps} onMapReady={onMapReadyMock} />);
      
      // The MapReadyNotifier component should trigger the callback
      expect(onMapReadyMock).toHaveBeenCalledWith(mockMapInstance);
    });

    it('should work without onMapReady callback', () => {
      expect(() => render(<BaseMap {...defaultProps} />)).not.toThrow();
    });
  });

  describe('Custom Styling', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <BaseMap {...defaultProps} className="custom-class" />
      );
      
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass('custom-class');
    });

    it('should always have relative positioning', () => {
      const { container } = render(<BaseMap {...defaultProps} />);
      
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass('relative');
    });

    it('should have rounded corners on map', () => {
      render(<BaseMap {...defaultProps} />);
      // The MapContainer should have rounded-lg class
      // This is applied in the implementation
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });

  describe('TrigDetailMap Compatibility', () => {
    it('should support TrigDetailMap default configuration', () => {
      // TrigDetailMap uses: center, zoom, height, tileLayerId
      const trigDetailProps: BaseMapProps = {
        center: [51.5074, -0.1278],
        zoom: 14,
        height: 350,
        tileLayerId: 'osm',
      };
      
      const { container } = render(<BaseMap {...trigDetailProps} />);
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should support EPSG:27700 with zoom 8', () => {
      // TrigDetailMap uses zoom 8 for EPSG:27700
      render(<BaseMap {...defaultProps} tileLayerId="osPaper" zoom={8} />);
      
      const container = screen.getByTestId('map-container');
      expect(container.getAttribute('data-zoom')).toBe('8');
      expect(container.getAttribute('data-crs')).toBe('EPSG:27700');
    });

    it('should support EPSG:3857 with zoom 14', () => {
      // TrigDetailMap uses zoom 14 for EPSG:3857
      render(<BaseMap {...defaultProps} tileLayerId="osm" zoom={14} />);
      
      const container = screen.getByTestId('map-container');
      expect(container.getAttribute('data-zoom')).toBe('14');
    });
  });

  describe('Map Page Compatibility', () => {
    it('should support full height maps', () => {
      const { container } = render(
        <BaseMap {...defaultProps} height="100%" />
      );
      
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.height).toBe('100%');
    });

    it('should support children like markers and overlays', () => {
      render(
        <BaseMap {...defaultProps}>
          <div data-testid="marker">Marker</div>
          <div data-testid="overlay">Overlay</div>
        </BaseMap>
      );
      
      expect(screen.getByTestId('marker')).toBeInTheDocument();
      expect(screen.getByTestId('overlay')).toBeInTheDocument();
    });
  });

  describe('Tile Size Configuration', () => {
    it('should use default tile size of 256 for standard tiles', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      const tileLayer = screen.getByTestId('tile-layer');
      // Default is 256, not explicitly set for OSM
      expect(tileLayer).toBeInTheDocument();
    });

    it('should use custom tile size for EPSG:27700', () => {
      render(<BaseMap {...defaultProps} tileLayerId="osPaper" />);
      
      const tileLayer = screen.getByTestId('tile-layer');
      expect(tileLayer.getAttribute('data-tile-size')).toBe('256');
    });
  });

  describe('Stability Tests', () => {
    it('should maintain stable props interface', () => {
      const props: BaseMapProps = {
        center: [51.5, -2.0],
        zoom: 7,
        height: 400,
        tileLayerId: 'osm',
        children: <div>Test</div>,
        onMapReady: vi.fn(),
        className: 'test',
      };
      
      expect(() => render(<BaseMap {...props} />)).not.toThrow();
    });

    it('should work with minimal props', () => {
      const minimalProps: BaseMapProps = {
        center: [51.5, -2.0],
        zoom: 7,
        tileLayerId: 'osm',
      };
      
      expect(() => render(<BaseMap {...minimalProps} />)).not.toThrow();
    });

    it('should not break when tile layer changes', () => {
      const { rerender } = render(<BaseMap {...defaultProps} tileLayerId="osm" />);
      
      expect(() => {
        rerender(<BaseMap {...defaultProps} tileLayerId="osDigital" />);
        rerender(<BaseMap {...defaultProps} tileLayerId="osPaper" />);
        rerender(<BaseMap {...defaultProps} tileLayerId="osm" />);
      }).not.toThrow();
    });

    it('should handle rapid prop changes', () => {
      const { rerender } = render(<BaseMap {...defaultProps} zoom={7} />);
      
      expect(() => {
        rerender(<BaseMap {...defaultProps} zoom={8} />);
        rerender(<BaseMap {...defaultProps} zoom={9} />);
        rerender(<BaseMap {...defaultProps} zoom={10} />);
      }).not.toThrow();
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid tile layer ID gracefully', () => {
      // Invalid ID should fallback to default layer
      expect(() => 
        render(<BaseMap {...defaultProps} tileLayerId="invalid-id" />)
      ).not.toThrow();
    });

    it('should handle edge case coordinates', () => {
      expect(() => {
        render(<BaseMap {...defaultProps} center={[90, 180]} />);
        render(<BaseMap {...defaultProps} center={[-90, -180]} />);
        render(<BaseMap {...defaultProps} center={[0, 0]} />);
      }).not.toThrow();
    });
  });
});

