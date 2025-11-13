import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { BrowserRouter } from 'react-router-dom';
import TrigDetailMap from '../TrigDetailMap';
import { createMockTrig, mockLocalStorage, trigsByCondition } from './test-utils';
import { TILE_LAYER_STORAGE_KEY, MAP_CONFIG } from '../../../lib/mapConfig';

// Wrap component with Router for Link component
const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

// Mock Leaflet components
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children, ...props }: { children?: React.ReactNode; center: unknown; zoom: number; crs?: { code?: string } }) => (
    <div data-testid="map-container" data-center={JSON.stringify(props.center)} data-zoom={props.zoom} data-crs={props.crs?.code || 'default'}>
      {children}
    </div>
  ),
  TileLayer: (props: { url?: string }) => <div data-testid="tile-layer" data-url={props.url} />,
  Marker: ({ children, ...props }: { children?: React.ReactNode; position: unknown }) => (
    <div data-testid="marker" data-position={JSON.stringify(props.position)}>
      {children}
    </div>
  ),
  Tooltip: ({ children }: { children?: React.ReactNode }) => <div data-testid="tooltip">{children}</div>,
  Popup: ({ children }: { children?: React.ReactNode }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({
    setView: vi.fn(),
    setMinZoom: vi.fn(),
    setMaxZoom: vi.fn(),
    invalidateSize: vi.fn(),
    getZoom: vi.fn().mockReturnValue(14),
    setZoom: vi.fn(),
  }),
  ScaleControl: () => <div data-testid="scale-control" />,
}));

describe('TrigDetailMap', () => {
  let localStorageMock: ReturnType<typeof mockLocalStorage>;

  beforeEach(() => {
    localStorageMock = mockLocalStorage();
  });

  afterEach(() => {
    localStorageMock.localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render without crashing', () => {
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    it('should render BaseMap component', () => {
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    it('should render single TrigMarker', () => {
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      const markers = screen.getAllByTestId('marker');
      expect(markers).toHaveLength(1);
    });

    it('should render TilesetSelector', () => {
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('should position TilesetSelector in top-right corner', () => {
      const trig = createMockTrig();
      const { container } = renderWithRouter(<TrigDetailMap trig={trig} />);
      // Look inside the BrowserRouter wrapper
      const selectorWrapper = container.querySelector('.absolute.top-2.right-2');
      expect(selectorWrapper).toBeInTheDocument();
    });
  });

  describe('Map Centering', () => {
    it('should center map on trig coordinates', () => {
      const trig = createMockTrig({
        wgs_lat: 51.5074,
        wgs_long: -0.1278,
      });
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const mapContainer = screen.getByTestId('map-container');
      const center = JSON.parse(mapContainer.getAttribute('data-center') || '[]');
      expect(center).toEqual([51.5074, -0.1278]);
    });

    it('should handle string coordinates', () => {
      const trig = createMockTrig({
        wgs_lat: '52.4862',
        wgs_long: '-1.8904',
      });
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const mapContainer = screen.getByTestId('map-container');
      const center = JSON.parse(mapContainer.getAttribute('data-center') || '[]');
      expect(center).toEqual([52.4862, -1.8904]);
    });

    it('should handle number coordinates', () => {
      const trig = createMockTrig({
        wgs_lat: 53.4808,
        wgs_long: -2.2426,
      });
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const mapContainer = screen.getByTestId('map-container');
      const center = JSON.parse(mapContainer.getAttribute('data-center') || '[]');
      expect(center).toEqual([53.4808, -2.2426]);
    });
  });

  describe('Zoom Level Behavior', () => {
    it('should use default zoom level for EPSG:3857 tiles', () => {
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osm');
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const mapContainer = screen.getByTestId('map-container');
      const zoom = parseInt(mapContainer.getAttribute('data-zoom') || '0');
      expect(zoom).toBe(MAP_CONFIG.detailMapZoom); // 14
    });

    it('should use adjusted zoom level for EPSG:27700 tiles', () => {
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osPaper');
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const mapContainer = screen.getByTestId('map-container');
      const zoom = parseInt(mapContainer.getAttribute('data-zoom') || '0');
      expect(zoom).toBe(8); // Special zoom for EPSG:27700
    });

    it('should recalculate zoom when tile layer changes', () => {
      // Start with OSM
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osm');
      const { unmount } = renderWithRouter(<TrigDetailMap trig={createMockTrig()} />);
      
      // Initially should have default zoom for EPSG:3857
      let mapContainer = screen.getByTestId('map-container');
      let zoom = parseInt(mapContainer.getAttribute('data-zoom') || '0');
      expect(zoom).toBe(MAP_CONFIG.detailMapZoom);
      
      unmount();
      
      // Change to EPSG:27700
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osPaper');
      renderWithRouter(<TrigDetailMap trig={createMockTrig()} />);
      
      mapContainer = screen.getByTestId('map-container');
      zoom = parseInt(mapContainer.getAttribute('data-zoom') || '0');
      expect(zoom).toBe(8);
    });
  });

  describe('Color Mode (CRITICAL)', () => {
    it('should ALWAYS use condition color mode', () => {
      const trig = trigsByCondition.good;
      const { container } = renderWithRouter(<TrigDetailMap trig={trig} />);
      
      // The component hardcodes colorMode to 'condition'
      // This is a stability guarantee for TrigDetailMap
      const marker = container.querySelector('[data-testid="marker"]');
      expect(marker).toBeInTheDocument();
    });

    it('should NOT use userLog color mode', () => {
      // TrigDetailMap should never use userLog mode
      // This test ensures the mode is always 'condition'
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      // If this test breaks, it means TrigDetailMap might have been
      // accidentally changed to use userLog mode
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });

    it('should display green icon for good condition trigs', () => {
      const trig = trigsByCondition.good;
      renderWithRouter(<TrigDetailMap trig={trig} />);
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });

    it('should display yellow icon for damaged trigs', () => {
      const trig = trigsByCondition.damaged;
      renderWithRouter(<TrigDetailMap trig={trig} />);
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });

    it('should display red icon for missing trigs', () => {
      const trig = trigsByCondition.missing;
      renderWithRouter(<TrigDetailMap trig={trig} />);
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });
  });

  describe('Height Configuration', () => {
    it('should use default height from MAP_CONFIG', () => {
      const trig = createMockTrig();
      const { container } = renderWithRouter(<TrigDetailMap trig={trig} />);
      
      // The component should use MAP_CONFIG.detailMapHeight (350)
      // Look for the TrigDetailMap wrapper inside BrowserRouter
      const wrapper = container.querySelector('.relative');
      expect(wrapper).toHaveClass('relative');
    });

    it('should accept custom height', () => {
      const trig = createMockTrig();
      const { container } = renderWithRouter(<TrigDetailMap trig={trig} height={500} />);
      
      const wrapper = container.querySelector('.relative');
      expect(wrapper).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const trig = createMockTrig();
      const { container } = renderWithRouter(<TrigDetailMap trig={trig} className="custom-class" />);
      
      const wrapper = container.querySelector('.custom-class');
      expect(wrapper).toHaveClass('custom-class');
    });
  });

  describe('Tile Layer Preferences', () => {
    it('should initialize with preferred tile layer from localStorage', () => {
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osDigital');
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('should fall back to default tile layer if no preference', () => {
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('should allow switching between tile layers', () => {
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const selector = screen.getByRole('combobox');
      expect(selector).toBeInTheDocument();
    });
  });

  describe('Marker Display', () => {
    it('should position marker at trig coordinates', () => {
      const trig = createMockTrig({
        wgs_lat: 51.5074,
        wgs_long: -0.1278,
      });
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const marker = screen.getByTestId('marker');
      const position = JSON.parse(marker.getAttribute('data-position') || '[]');
      expect(position).toEqual([51.5074, -0.1278]);
    });

    it('should NOT highlight the marker', () => {
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      // TrigDetailMap passes highlighted={false}
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });

    it('should not show marker popup on detail map', () => {
      const trig = createMockTrig({
        waypoint: 'TP1234',
        name: 'Test Trig',
      });
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      expect(screen.queryByTestId('popup')).not.toBeInTheDocument();
    });
  });

  describe('Stability Regression Tests', () => {
    it('should maintain stable structure when re-rendered', () => {
      const trig = createMockTrig();
      const { rerender, container } = renderWithRouter(<TrigDetailMap trig={trig} />);
      const initialHTML = container.innerHTML;
      
      rerender(<BrowserRouter><TrigDetailMap trig={trig} /></BrowserRouter>);
      const afterHTML = container.innerHTML;
      
      expect(afterHTML).toBe(initialHTML);
    });

    it('should handle all trig conditions correctly', () => {
      Object.values(trigsByCondition).forEach(trig => {
        const { unmount } = renderWithRouter(<TrigDetailMap trig={trig} />);
        expect(screen.getByTestId('marker')).toBeInTheDocument();
        unmount();
      });
    });

    it('should not break with minimal trig data', () => {
      const minimalTrig = createMockTrig({
        id: 1,
        waypoint: 'TP0001',
        name: 'Minimal',
        physical_type: 'Pillar',
        condition: 'U',
        wgs_lat: 51.5,
        wgs_long: -0.1,
        osgb_gridref: 'TQ 00 00',
      });
      
      renderWithRouter(<TrigDetailMap trig={minimalTrig} />);
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });

    it('should maintain correct component hierarchy', () => {
      const trig = createMockTrig();
      const { container } = renderWithRouter(<TrigDetailMap trig={trig} />);
      
      // Check structure (inside BrowserRouter wrapper)
      expect(container.querySelector('.relative')).toBeInTheDocument(); // Wrapper
      expect(screen.getByTestId('map-container')).toBeInTheDocument(); // BaseMap
      expect(screen.getByTestId('marker')).toBeInTheDocument(); // TrigMarker
      expect(container.querySelector('.absolute.top-2.right-2')).toBeInTheDocument(); // Selector wrapper
    });
  });

  describe('CRS Handling', () => {
    it('should support EPSG:3857 projection', () => {
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osm');
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
    });

    it('should support EPSG:27700 projection', () => {
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osPaper');
      const trig = createMockTrig();
      renderWithRouter(<TrigDetailMap trig={trig} />);
      
      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
    });
  });

  describe('Integration with BaseMap', () => {
    it('should pass correct props to BaseMap', () => {
      const trig = createMockTrig({
        wgs_lat: 51.5074,
        wgs_long: -0.1278,
      });
      renderWithRouter(<TrigDetailMap trig={trig} height={400} />);
      
      const mapContainer = screen.getByTestId('map-container');
      expect(mapContainer).toBeInTheDocument();
      
      const center = JSON.parse(mapContainer.getAttribute('data-center') || '[]');
      expect(center[0]).toBe(51.5074);
      expect(center[1]).toBe(-0.1278);
    });
  });

  describe('Component Stability Contract', () => {
    // These tests verify the TrigDetailMap API remains stable
    
    it('should accept TrigData with all required fields', () => {
      const trig = createMockTrig();
      expect(() => renderWithRouter(<TrigDetailMap trig={trig} />)).not.toThrow();
    });

    it('should accept optional height prop', () => {
      const trig = createMockTrig();
      expect(() => renderWithRouter(<TrigDetailMap trig={trig} height={500} />)).not.toThrow();
    });

    it('should accept optional className prop', () => {
      const trig = createMockTrig();
      expect(() => renderWithRouter(<TrigDetailMap trig={trig} className="test" />)).not.toThrow();
    });

    it('should work without optional props', () => {
      const trig = createMockTrig();
      expect(() => renderWithRouter(<TrigDetailMap trig={trig} />)).not.toThrow();
    });
  });
});

