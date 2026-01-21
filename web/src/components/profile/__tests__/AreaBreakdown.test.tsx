import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AreaBreakdown from '../AreaBreakdown';
import { ReactNode } from 'react';

// Mock the hooks
vi.mock('../../../hooks/useAreaTypes', () => ({
  useAreaTypes: vi.fn(),
}));

vi.mock('../../../hooks/useUserAreaBreakdown', () => ({
  useUserAreaBreakdown: vi.fn(),
}));

import { useAreaTypes } from '../../../hooks/useAreaTypes';
import { useUserAreaBreakdown } from '../../../hooks/useUserAreaBreakdown';

const mockUseAreaTypes = useAreaTypes as ReturnType<typeof vi.fn>;
const mockUseUserAreaBreakdown = useUserAreaBreakdown as ReturnType<typeof vi.fn>;

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockAreaTypes = [
  {
    id: 1,
    code: 'county_1991',
    name: 'County (1991)',
    description: 'Counties as defined in 1991',
  },
  {
    id: 2,
    code: 'historic_county',
    name: 'Historic County',
    description: 'Traditional historic counties',
  },
];

const mockBreakdownData = {
  area_type: {
    id: 1,
    code: 'county_1991',
    name: 'County (1991)',
    description: 'Counties as defined in 1991',
  },
  items: [
    { area_name: 'Greater London', count: 15 },
    { area_name: 'Greater Manchester', count: 8 },
    { area_name: 'West Yorkshire', count: 5 },
  ],
};

describe('AreaBreakdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('loading states', () => {
    it('should show spinner while loading area types', () => {
      mockUseAreaTypes.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      expect(screen.getByText('Area')).toBeInTheDocument();
      // Should have a spinner (check for the Spinner component's output)
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should show spinner while loading breakdown data', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      expect(screen.getByText('Area')).toBeInTheDocument();
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('rendering data', () => {
    it('should render area type dropdown with options', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: mockBreakdownData,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      const dropdown = screen.getByRole('combobox');
      expect(dropdown).toBeInTheDocument();

      // Check options
      const options = screen.getAllByRole('option');
      expect(options).toHaveLength(2);
      expect(options[0]).toHaveTextContent('County (1991)');
      expect(options[1]).toHaveTextContent('Historic County');
    });

    it('should render area type description', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: mockBreakdownData,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      expect(
        screen.getByText('Counties as defined in 1991')
      ).toBeInTheDocument();
    });

    it('should render area count items', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: mockBreakdownData,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      expect(screen.getByText('Greater London')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getByText('Greater Manchester')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument();
      expect(screen.getByText('West Yorkshire')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('should show "No data" message when items is empty', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: {
          area_type: mockBreakdownData.area_type,
          items: [],
        },
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      expect(screen.getByText('No data for this area type')).toBeInTheDocument();
    });
  });

  describe('dropdown interaction', () => {
    it('should change selected area type when dropdown changes', async () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: mockBreakdownData,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      const dropdown = screen.getByRole('combobox');
      fireEvent.change(dropdown, { target: { value: 'historic_county' } });

      expect(dropdown).toHaveValue('historic_county');
    });

    it('should default to county_1991', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: mockBreakdownData,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      const dropdown = screen.getByRole('combobox');
      expect(dropdown).toHaveValue('county_1991');
    });
  });

  describe('error handling', () => {
    it('should show error message when breakdown fetch fails', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      expect(
        screen.getByText('Failed to load area breakdown')
      ).toBeInTheDocument();
    });
  });

  describe('description handling', () => {
    it('should not render description box when description is null', () => {
      const breakdownWithNoDescription = {
        area_type: {
          id: 1,
          code: 'county_1991',
          name: 'County (1991)',
          description: null,
        },
        items: mockBreakdownData.items,
      };

      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: breakdownWithNoDescription,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      // Description box should not be present
      expect(
        screen.queryByText('Counties as defined in 1991')
      ).not.toBeInTheDocument();
    });
  });

  describe('userId prop', () => {
    it('should accept numeric userId', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: mockBreakdownData,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId={123} />, { wrapper: createWrapper() });

      expect(mockUseUserAreaBreakdown).toHaveBeenCalledWith(123, 'county_1991');
    });

    it('should accept string userId', () => {
      mockUseAreaTypes.mockReturnValue({
        data: mockAreaTypes,
        isLoading: false,
        error: null,
      });
      mockUseUserAreaBreakdown.mockReturnValue({
        data: mockBreakdownData,
        isLoading: false,
        error: null,
      });

      render(<AreaBreakdown userId="456" />, { wrapper: createWrapper() });

      expect(mockUseUserAreaBreakdown).toHaveBeenCalledWith('456', 'county_1991');
    });
  });
});

