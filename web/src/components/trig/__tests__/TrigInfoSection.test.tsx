import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TrigInfoSection from '../TrigInfoSection';

// Mock the hooks
vi.mock('../../../hooks/useUserProfile', () => ({
  useUserProfile: vi.fn(() => ({
    data: null,
    isLoading: false,
  })),
}));

vi.mock('../../../hooks/useAreasContaining', () => ({
  useAreasContaining: vi.fn(() => ({
    data: {
      groups: [
        {
          areas: [
            { id: 1, name: 'Test County', area_type: { name: 'County' } },
            { id: 2, name: 'Test District', area_type: { name: 'District' } },
          ],
        },
      ],
    },
    isLoading: false,
  })),
}));

// Mock import.meta.env
vi.stubGlobal('import', {
  meta: {
    env: {
      VITE_API_BASE: 'https://api.example.com',
    },
  },
});

// Create a mock trig
const createMockTrig = (overrides = {}) => ({
  id: 12345,
  waypoint: 'TP1234',
  name: 'Test Hill',
  condition: 'G',
  wgs_lat: '51.5074',
  wgs_long: '-0.1278',
  osgb_gridref: 'TQ123456',
  grid_system: 'gb' as const,
  type_code: 'HOTINE',
  type_name: 'Hotine Pillar',
  category_code: 'PILLAR',
  category_name: 'Pillar',
  details: {
    osgb_height: 100,
    wgs_height: 100.5,
    postcode: 'SW1A 1AA',
    current_use: 'None',
    historic_use: 'Triangulation',
    county: 'Test County',
    town: 'Test Town',
    fb_number: 'S1234',
    stn_number: 'SN123',
    stn_number_active: '',
    stn_number_passive: 'P123456',
    stn_number_osgb36: '',
    legal_message: null,
  },
  ...overrides,
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('TrigInfoSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('should render trig waypoint and name as a link', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    const link = screen.getByRole('link', { name: 'TP1234 - Test Hill' });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/trigs/12345');
  });

  it('should render grid reference', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Grid reference:/i)).toBeInTheDocument();
    expect(screen.getByText('TQ123456')).toBeInTheDocument();
  });

  it('should render WGS coordinates', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/WGS coordinates:/i)).toBeInTheDocument();
    expect(screen.getByText('51.5074, -0.1278')).toBeInTheDocument();
  });

  it('should render height above sea level when available', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Height above sea level:/i)).toBeInTheDocument();
    expect(screen.getByText('100m')).toBeInTheDocument();
  });

  it('should not render height when not available', () => {
    const mockTrig = createMockTrig({
      details: {
        ...createMockTrig().details,
        osgb_height: null,
      },
    });
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.queryByText(/Height above sea level:/i)).not.toBeInTheDocument();
  });

  it('should render postcode as Google Maps link when available', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Postcode:/i)).toBeInTheDocument();
    const postcodeLink = screen.getByRole('link', { name: 'SW1A 1AA' });
    expect(postcodeLink).toHaveAttribute('href', 'https://www.google.co.uk/maps/search/SW1A%201AA');
  });

  it('should render type name with wiki link', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Type:/i)).toBeInTheDocument();
    // When category_code != type_code, shows "Category · Type"
    const typeLink = screen.getByRole('link', { name: 'Pillar · Hotine Pillar' });
    expect(typeLink).toHaveAttribute('href', 'https://wiki.trigpointing.uk/Hotine_Pillar');
  });

  it('should render condition badge', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Condition:/i)).toBeInTheDocument();
    expect(screen.getByText('Good')).toBeInTheDocument();
  });

  it('should render flush bracket number when available', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Flush Bracket:/i)).toBeInTheDocument();
    expect(screen.getByText('S1234')).toBeInTheDocument();
  });

  it('should render passive station as OS link', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Passive Station:/i)).toBeInTheDocument();
    const passiveLink = screen.getByRole('link', { name: 'P123456' });
    expect(passiveLink).toHaveAttribute(
      'href',
      'https://www.ordnancesurvey.co.uk/geodesy-positioning/legacy-data/passive-search/passive-station/P123456'
    );
  });

  it('should render county and town', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/County:/i)).toBeInTheDocument();
    expect(screen.getByText('Test County')).toBeInTheDocument();
    expect(screen.getByText(/Nearest town:/i)).toBeInTheDocument();
    expect(screen.getByText('Test Town')).toBeInTheDocument();
  });

  it('should render interactive map link', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    const mapLink = screen.getByRole('link', { name: /View on Interactive Map/i });
    expect(mapLink).toHaveAttribute('href', '/map?lat=51.5074&lon=-0.1278&trig=12345');
  });

  it('should render photo album link', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    const photoLink = screen.getByRole('link', { name: /View Photo Album/i });
    expect(photoLink).toHaveAttribute('href', '/trigs/12345/photos');
  });

  it('should render nearby trigpoints dropdown when showNearbyDropdown is true', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} showNearbyDropdown={true} />);
    
    const dropdownButton = screen.getByRole('button', { name: /View Nearby Trigpoints/i });
    expect(dropdownButton).toBeInTheDocument();
  });

  it('should not render nearby trigpoints dropdown when showNearbyDropdown is false', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} showNearbyDropdown={false} />);
    
    const dropdownButton = screen.queryByRole('button', { name: /View Nearby Trigpoints/i });
    expect(dropdownButton).not.toBeInTheDocument();
  });

  it('should open dropdown when clicked', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    const dropdownButton = screen.getByRole('button', { name: /View Nearby Trigpoints/i });
    fireEvent.click(dropdownButton);
    
    expect(screen.getByText('All nearby trigpoints')).toBeInTheDocument();
    // "County" appears as area type in dropdown
    const countyElements = screen.getAllByText('County');
    expect(countyElements.length).toBeGreaterThanOrEqual(1);
    // "Test County" appears both in the details section and in the dropdown
    const testCountyElements = screen.getAllByText('Test County');
    expect(testCountyElements.length).toBeGreaterThanOrEqual(2);
  });

  it('should render map thumbnail image', () => {
    const mockTrig = createMockTrig();
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    const thumbnail = screen.getByAltText('Map thumbnail for Test Hill');
    expect(thumbnail).toBeInTheDocument();
  });

  it('should render Irish grid reference label for Irish trigs', () => {
    const mockTrig = createMockTrig({
      grid_system: 'ie',
    });
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    expect(screen.getByText(/Grid reference \(Irish\):/i)).toBeInTheDocument();
  });

  it('should handle different condition codes', () => {
    const conditions = [
      { code: 'G', label: 'Good' },
      { code: 'S', label: 'Slightly Damaged' },
      { code: 'D', label: 'Damaged' },
      { code: 'M', label: 'Moved' },
      { code: 'X', label: 'Destroyed' },
      { code: 'U', label: 'Unknown' },
    ];

    conditions.forEach(({ code, label }) => {
      const mockTrig = createMockTrig({ condition: code });
      const { unmount } = renderWithProviders(<TrigInfoSection trig={mockTrig} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    });
  });

  it('should handle trig without details', () => {
    const mockTrig = createMockTrig({ details: undefined });
    renderWithProviders(<TrigInfoSection trig={mockTrig} />);
    
    // Should still render basic info
    expect(screen.getByText('TP1234 - Test Hill')).toBeInTheDocument();
    expect(screen.getByText('TQ123456')).toBeInTheDocument();
    
    // Should not render detail fields
    expect(screen.queryByText(/Height above sea level:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Postcode:/i)).not.toBeInTheDocument();
  });

  it('should accept custom className', () => {
    const mockTrig = createMockTrig();
    const { container } = renderWithProviders(
      <TrigInfoSection trig={mockTrig} className="custom-class" />
    );
    
    // The Card component should have the custom class
    const card = container.querySelector('.custom-class');
    expect(card).toBeInTheDocument();
  });
});

