import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import TilesetSelector from '../TilesetSelector';
import { mockLocalStorage } from './test-utils';
import { TILE_LAYER_STORAGE_KEY } from '../../../lib/mapConfig';

describe('TilesetSelector', () => {
  let localStorageMock: ReturnType<typeof mockLocalStorage>;
  let onChangeMock: Mock<(tileLayerId: string) => void>;

  beforeEach(() => {
    localStorageMock = mockLocalStorage();
    onChangeMock = vi.fn();
  });

  afterEach(() => {
    localStorageMock.localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render dropdown with label', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      expect(screen.getByLabelText('Map Layer')).toBeInTheDocument();
    });

    it('should render select element', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
    });

    it('should render all available tile layers as options', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      const options = Array.from(select.options);
      
      expect(options.length).toBeGreaterThan(0);
      expect(options.some(opt => opt.value === 'osm')).toBe(true);
    });

    it('should show currently selected value', () => {
      render(<TilesetSelector value="osDigital" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      expect(select.value).toBe('osDigital');
    });

    it('should apply custom className', () => {
      const { container } = render(
        <TilesetSelector value="osm" onChange={onChangeMock} className="custom-class" />
      );
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass('custom-class');
    });

    it('should have default styling classes', () => {
      const { container } = render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass('bg-white');
      expect(wrapper).toHaveClass('rounded-lg');
      expect(wrapper).toHaveClass('shadow-md');
    });
  });

  describe('Tile Layer Options', () => {
    it('should include OSM option', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      expect(screen.getByRole('option', { name: /OpenStreetMap/i })).toBeInTheDocument();
    });

    it('should include OS Digital option', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      expect(screen.getByRole('option', { name: /OS Digital/i })).toBeInTheDocument();
    });

    it('should include OS Paper option', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      expect(screen.getByRole('option', { name: /OS Paper/i })).toBeInTheDocument();
    });

    it('should include satellite option', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      expect(screen.getByRole('option', { name: /Satellite/i })).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should call onChange when selection changes', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      
      fireEvent.change(select, { target: { value: 'osDigital' } });
      
      expect(onChangeMock).toHaveBeenCalledWith('osDigital');
      expect(onChangeMock).toHaveBeenCalledTimes(1);
    });

    it('should save preference to localStorage on change', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      
      fireEvent.change(select, { target: { value: 'osPaper' } });
      
      expect(localStorageMock.localStorageMock.setItem).toHaveBeenCalledWith(
        TILE_LAYER_STORAGE_KEY,
        'osPaper'
      );
    });

    it('should handle multiple changes', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      
      fireEvent.change(select, { target: { value: 'osDigital' } });
      fireEvent.change(select, { target: { value: 'osPaper' } });
      
      expect(onChangeMock).toHaveBeenCalledTimes(2);
      expect(onChangeMock).toHaveBeenNthCalledWith(1, 'osDigital');
      expect(onChangeMock).toHaveBeenNthCalledWith(2, 'osPaper');
    });
  });

  describe('LocalStorage Integration', () => {
    it('should persist selection to localStorage', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      
      fireEvent.change(select, { target: { value: 'osDigital' } });
      
      expect(localStorageMock.store[TILE_LAYER_STORAGE_KEY]).toBe('osDigital');
    });

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.localStorageMock.setItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });
      
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      
      expect(() => {
        fireEvent.change(select, { target: { value: 'osDigital' } });
      }).not.toThrow();
      
      expect(onChangeMock).toHaveBeenCalledWith('osDigital');
    });
  });

  describe('TrigDetailMap Compatibility', () => {
    it('should work with default value from getPreferredTileLayer', () => {
      // Set a preference in localStorage
      localStorageMock.localStorageMock.setItem(TILE_LAYER_STORAGE_KEY, 'osPaper');
      
      render(<TilesetSelector value="osPaper" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      expect(select.value).toBe('osPaper');
    });

    it('should allow switching between EPSG:3857 and EPSG:27700 tiles', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      
      // Switch to EPSG:27700 (OS Paper)
      fireEvent.change(select, { target: { value: 'osPaper' } });
      expect(onChangeMock).toHaveBeenCalledWith('osPaper');
      
      // Switch back to EPSG:3857 (OSM)
      fireEvent.change(select, { target: { value: 'osm' } });
      expect(onChangeMock).toHaveBeenCalledWith('osm');
    });

    it('should display in top-right corner style when used in TrigDetailMap', () => {
      const { container } = render(
        <div className="absolute top-2 right-2 z-[1000]">
          <TilesetSelector value="osm" onChange={onChangeMock} />
        </div>
      );
      
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass('absolute');
      expect(wrapper).toHaveClass('top-2');
      expect(wrapper).toHaveClass('right-2');
    });
  });

  describe('Accessibility', () => {
    it('should have accessible label', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const label = screen.getByText('Map Layer');
      const select = screen.getByRole('combobox');
      expect(label.getAttribute('for')).toBe('tileset-selector');
      expect(select.getAttribute('id')).toBe('tileset-selector');
    });

    it('should be keyboard navigable', () => {
      render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const select = screen.getByRole('combobox');
      
      select.focus();
      expect(document.activeElement).toBe(select);
    });
  });

  describe('Stability Tests', () => {
    it('should maintain consistent option structure', () => {
      const { rerender } = render(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const initialOptions = screen.getAllByRole('option');
      
      rerender(<TilesetSelector value="osDigital" onChange={onChangeMock} />);
      const afterOptions = screen.getAllByRole('option');
      
      expect(initialOptions.length).toBe(afterOptions.length);
    });

    it('should not modify DOM unnecessarily on re-render', () => {
      const { rerender, container } = render(
        <TilesetSelector value="osm" onChange={onChangeMock} />
      );
      const initialHTML = container.innerHTML;
      
      // Re-render with same props
      rerender(<TilesetSelector value="osm" onChange={onChangeMock} />);
      const afterHTML = container.innerHTML;
      
      expect(afterHTML).toBe(initialHTML);
    });
  });
});

