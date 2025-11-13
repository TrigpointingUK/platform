import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import TrigMarker from '../TrigMarker';
import { createMockTrig, trigsByCondition, trigsByPhysicalType } from './test-utils';
import type { UserLogStatus } from '../../../lib/mapIcons';

// Mock react-leaflet components
vi.mock('react-leaflet', () => ({
  Marker: ({ children, eventHandlers, ...props }: { children?: React.ReactNode; position: unknown; icon?: { options?: { iconUrl?: string } }; eventHandlers?: { click?: () => void } }) => (
    <div 
      data-testid="marker"
      data-position={JSON.stringify(props.position)}
      data-icon-url={props.icon?.options?.iconUrl}
      onClick={() => eventHandlers?.click?.()}
    >
      {children}
    </div>
  ),
  Tooltip: ({ children }: { children?: React.ReactNode }) => <div data-testid="tooltip">{children}</div>,
  Popup: ({ children }: { children?: React.ReactNode }) => <div data-testid="popup">{children}</div>,
}));

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  Link: ({ to, children, ...props }: { to: string; children?: React.ReactNode; className?: string }) => (
    <a href={to} {...props}>{children}</a>
  ),
}));

describe('TrigMarker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render without crashing', () => {
      const trig = createMockTrig();
      render(<TrigMarker trig={trig} colorMode="condition" />);
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });

    it('should render marker at correct position', () => {
      const trig = createMockTrig({
        wgs_lat: 51.5074,
        wgs_long: -0.1278,
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const position = JSON.parse(marker.getAttribute('data-position') || '[]');
      expect(position).toEqual([51.5074, -0.1278]);
    });

    it('should render popup with trig information', () => {
      const trig = createMockTrig();
      render(<TrigMarker trig={trig} colorMode="condition" />);
      expect(screen.getByTestId('popup')).toBeInTheDocument();
    });

    it('should handle string coordinates', () => {
      const trig = createMockTrig({
        wgs_lat: '52.4862',
        wgs_long: '-1.8904',
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const position = JSON.parse(marker.getAttribute('data-position') || '[]');
      expect(position).toEqual([52.4862, -1.8904]);
    });

    it('should handle number coordinates', () => {
      const trig = createMockTrig({
        wgs_lat: 53.4808,
        wgs_long: -2.2426,
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const position = JSON.parse(marker.getAttribute('data-position') || '[]');
      expect(position).toEqual([53.4808, -2.2426]);
    });
  });

  describe('Condition Color Mode', () => {
    it('should use green icon for good condition', () => {
      const trig = trigsByCondition.good;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('green');
    });

    it('should use yellow icon for damaged condition', () => {
      const trig = trigsByCondition.damaged;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('yellow');
    });

    it('should use red icon for missing condition', () => {
      const trig = trigsByCondition.missing;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('red');
    });

    it('should use red icon for possibly missing condition', () => {
      const trig = trigsByCondition.possibly;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('red');
    });

    it('should use grey icon for unknown condition', () => {
      const trig = trigsByCondition.unknown;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('grey');
    });
  });

  describe('UserLog Color Mode', () => {
    it('should use grey icon when not logged', () => {
      const trig = createMockTrig();
      render(<TrigMarker trig={trig} colorMode="userLog" logStatus={null} />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('grey');
    });

    it('should use green icon when logged as found', () => {
      const trig = createMockTrig();
      const logStatus: UserLogStatus = { hasLogged: true, foundStatus: true };
      render(<TrigMarker trig={trig} colorMode="userLog" logStatus={logStatus} />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('green');
    });

    it('should use red icon when logged as not found', () => {
      const trig = createMockTrig();
      const logStatus: UserLogStatus = { hasLogged: true, foundStatus: false };
      render(<TrigMarker trig={trig} colorMode="userLog" logStatus={logStatus} />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('red');
    });

    it('should use grey icon when no log status provided', () => {
      const trig = createMockTrig();
      render(<TrigMarker trig={trig} colorMode="userLog" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('grey');
    });
  });

  describe('Physical Type Icons', () => {
    it('should use pillar icon for Pillar type', () => {
      const trig = trigsByPhysicalType.pillar;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('pillar');
    });

    it('should use fbm icon for FBM type', () => {
      const trig = trigsByPhysicalType.fbm;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('fbm');
    });

    it('should use passive icon for Passive Station type', () => {
      const trig = trigsByPhysicalType.passive;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('passive');
    });

    it('should use intersected icon for Intersection type', () => {
      const trig = trigsByPhysicalType.intersection;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('intersected');
    });

    it('should fallback to pillar icon for Bolt type', () => {
      const trig = trigsByPhysicalType.bolt;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('pillar');
    });

    it('should fallback to passive icon for Active Station type', () => {
      const trig = trigsByPhysicalType.active;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('passive');
    });

    it('should fallback to pillar icon for Other type', () => {
      const trig = trigsByPhysicalType.other;
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('pillar');
    });
  });

  describe('Highlighted State', () => {
    it('should not add highlight suffix by default', () => {
      const trig = createMockTrig();
      render(<TrigMarker trig={trig} colorMode="condition" highlighted={false} />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).not.toContain('_h.png');
    });

    it('should add highlight suffix when highlighted', () => {
      const trig = createMockTrig();
      render(<TrigMarker trig={trig} colorMode="condition" highlighted={true} />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('_h.png');
    });
  });

  describe('Popup Content', () => {
    it('should display waypoint and name in popup', () => {
      const trig = createMockTrig({
        waypoint: 'TP1234',
        name: 'Test Trig Point',
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      // Check popup content (more specific)
      const popup = screen.getByTestId('popup');
      expect(popup).toHaveTextContent(/TP1234/);
      expect(popup).toHaveTextContent(/Test Trig Point/);
      
      // Check tooltip content
      const tooltip = screen.getByTestId('tooltip');
      expect(tooltip).toHaveTextContent('Test Trig Point');
    });

    it('should display physical type in popup', () => {
      const trig = createMockTrig({
        physical_type: 'Pillar',
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      expect(screen.getByText(/Type:/)).toBeInTheDocument();
      expect(screen.getByText(/Pillar/)).toBeInTheDocument();
    });

    it('should display grid reference in popup', () => {
      const trig = createMockTrig({
        osgb_gridref: 'TQ 30 80',
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      expect(screen.getByText(/Grid ref:/)).toBeInTheDocument();
      expect(screen.getByText(/TQ 30 80/)).toBeInTheDocument();
    });

    it('should display coordinates in popup', () => {
      const trig = createMockTrig({
        wgs_lat: 51.5074,
        wgs_long: -0.1278,
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      expect(screen.getByText(/Coordinates:/)).toBeInTheDocument();
      expect(screen.getByText(/51.50740/)).toBeInTheDocument();
      expect(screen.getByText(/-0.12780/)).toBeInTheDocument();
    });

    it('should include link to trig detail page', () => {
      const trig = createMockTrig({ id: 123 });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const link = screen.getByText('View Details');
      expect(link).toBeInTheDocument();
      expect(link.closest('a')).toHaveAttribute('href', '/trig/123');
    });
  });

  describe('Click Handler', () => {
    it('should call onClick when marker is clicked', () => {
      const trig = createMockTrig();
      const onClickMock = vi.fn();
      render(<TrigMarker trig={trig} colorMode="condition" onClick={onClickMock} />);
      
      const marker = screen.getByTestId('marker');
      fireEvent.click(marker);
      
      expect(onClickMock).toHaveBeenCalledWith(trig);
      expect(onClickMock).toHaveBeenCalledTimes(1);
    });

    it('should not error when onClick is not provided', () => {
      const trig = createMockTrig();
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      expect(() => fireEvent.click(marker)).not.toThrow();
    });
  });

  describe('Icon URL Construction', () => {
    it('should construct correct icon URL path', () => {
      const trig = createMockTrig({
        physical_type: 'Pillar',
        condition: 'G',
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toBe('/icons/mapicon_pillar_green.png');
    });

    it('should use correct path structure for all combinations', () => {
      const trig = createMockTrig({
        physical_type: 'FBM',
        condition: 'D',
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toMatch(/^\/icons\/mapicon_\w+_\w+\.png$/);
    });
  });

  describe('Stability and Compatibility', () => {
    it('should maintain stable marker structure on re-render', () => {
      const trig = createMockTrig();
      const { rerender, container } = render(
        <TrigMarker trig={trig} colorMode="condition" />
      );
      const initialHTML = container.innerHTML;
      
      rerender(<TrigMarker trig={trig} colorMode="condition" />);
      const afterHTML = container.innerHTML;
      
      expect(afterHTML).toBe(initialHTML);
    });

    it('should work with TrigDetailMap color mode', () => {
      // TrigDetailMap always uses condition mode
      const trig = createMockTrig({ condition: 'G' });
      render(<TrigMarker trig={trig} colorMode="condition" highlighted={false} />);
      
      const marker = screen.getByTestId('marker');
      const iconUrl = marker.getAttribute('data-icon-url');
      expect(iconUrl).toContain('green');
    });

    it('should work with Map page color modes', () => {
      // Map page can switch between modes
      const trig = createMockTrig({ condition: 'G' });
      const logStatus: UserLogStatus = { hasLogged: true, foundStatus: false };
      
      const { rerender } = render(
        <TrigMarker trig={trig} colorMode="condition" />
      );
      let marker = screen.getByTestId('marker');
      expect(marker.getAttribute('data-icon-url')).toContain('green');
      
      rerender(<TrigMarker trig={trig} colorMode="userLog" logStatus={logStatus} />);
      marker = screen.getByTestId('marker');
      expect(marker.getAttribute('data-icon-url')).toContain('red');
    });
  });

  describe('Edge Cases', () => {
    it('should handle trig with minimal data', () => {
      const minimalTrig = {
        id: 1,
        waypoint: 'TP0001',
        name: 'Minimal',
        physical_type: 'Other',
        condition: 'U',
        wgs_lat: 51,
        wgs_long: 0,
        osgb_gridref: 'TQ 00 00',
      };
      
      expect(() => 
        render(<TrigMarker trig={minimalTrig} colorMode="condition" />)
      ).not.toThrow();
    });

    it('should format coordinates to 5 decimal places', () => {
      const trig = createMockTrig({
        wgs_lat: 51.507351,
        wgs_long: -0.127758,
      });
      render(<TrigMarker trig={trig} colorMode="condition" />);
      
      expect(screen.getByText(/51.50735/)).toBeInTheDocument();
      expect(screen.getByText(/-0.12776/)).toBeInTheDocument();
    });
  });
});

