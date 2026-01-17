import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useInfiniteTrigs } from '../useInfiniteTrigs';
import { ReactNode } from 'react';

// Mock Auth0
vi.mock('@auth0/auth0-react', () => ({
  useAuth0: () => ({
    isAuthenticated: false,
    getAccessTokenSilently: vi.fn(),
  }),
}));

// Mock authenticated fetch
vi.mock('../../lib/api', () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock fetch
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Mock environment variable
vi.stubEnv('VITE_API_BASE', 'http://localhost:8000');

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

const mockTrigsResponse = {
  items: [
    {
      id: 1,
      waypoint: 'TP0001',
      name: 'Test Trig 1',
      physical_type: 'Pillar',
      condition: 'G',
      wgs_lat: '51.5',
      wgs_long: '-0.1',
      osgb_gridref: 'TQ 30000 80000',
      group_code: 'PILLAR',
      group_name: 'Pillar',
    },
    {
      id: 2,
      waypoint: 'TP0002',
      name: 'Test Trig 2',
      physical_type: 'FBM',
      condition: 'G',
      wgs_lat: '51.6',
      wgs_long: '-0.2',
      osgb_gridref: 'TQ 30100 80100',
      group_code: 'FBM',
      group_name: 'FBM',
    },
  ],
  pagination: {
    total: 100,
    limit: 50,
    offset: 0,
    has_more: true,
  },
  links: {
    self: '/v1/trigs?skip=0',
    next: '/v1/trigs?skip=50',
    prev: null,
  },
};

describe('useInfiniteTrigs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe('basic functionality', () => {
    it('should not fetch when location is not set', async () => {
      const { result } = renderHook(() => useInfiniteTrigs(), {
        wrapper: createWrapper(),
      });

      // Query should be disabled (not fetching)
      expect(result.current.isFetching).toBe(false);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should fetch when location is set', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      const { result } = renderHook(
        () => useInfiniteTrigs({ lat: 51.5, lon: -0.1 }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalled();
      expect(result.current.data?.pages[0].items).toHaveLength(2);
    });
  });

  describe('groups parameter', () => {
    it('should send groups param when statusIds provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            statusIds: [10, 20], // PILLAR (10) and FBM (20)
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      expect(fetchCall).toContain('groups=PILLAR%2CFBM');
    });

    it('should convert all status IDs to group codes', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            statusIds: [10, 20, 30, 40, 50, 60],
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      // URL-encoded comma is %2C
      expect(fetchCall).toContain('groups=');
      expect(fetchCall).toContain('PILLAR');
      expect(fetchCall).toContain('FBM');
      expect(fetchCall).toContain('SURVEY_MARK');
      expect(fetchCall).toContain('INTERSECTED');
      expect(fetchCall).toContain('ACTIVE');
      expect(fetchCall).toContain('OTHER');
    });

    it('should not send groups param when statusIds is empty', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            statusIds: [],
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      expect(fetchCall).not.toContain('groups=');
    });
  });

  describe('log filter parameters', () => {
    it('should send exclude_found when showLogged is false', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            showLogged: false,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      expect(fetchCall).toContain('exclude_found=true');
    });

    it('should send only_found when showNotLogged is false', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            showNotLogged: false,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      expect(fetchCall).toContain('only_found=true');
    });

    it('should not send log filters when both are true (default)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            showLogged: true,
            showNotLogged: true,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      expect(fetchCall).not.toContain('exclude_found');
      expect(fetchCall).not.toContain('only_found');
    });
  });

  describe('distance and area parameters', () => {
    it('should send max_km param when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            maxKm: 200,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      expect(fetchCall).toContain('max_km=200');
    });

    it('should send area_id param when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      renderHook(
        () =>
          useInfiniteTrigs({
            lat: 51.5,
            lon: -0.1,
            areaId: 42,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchCall = mockFetch.mock.calls[0][0] as string;
      expect(fetchCall).toContain('area_id=42');
    });
  });

  describe('pagination', () => {
    it('should include pagination info in response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrigsResponse,
      } as Response);

      const { result } = renderHook(
        () => useInfiniteTrigs({ lat: 51.5, lon: -0.1 }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.pages[0].pagination.total).toBe(100);
      expect(result.current.data?.pages[0].pagination.has_more).toBe(true);
      expect(result.current.hasNextPage).toBe(true);
    });
  });

  describe('error handling', () => {
    it('should handle fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response);

      const { result } = renderHook(
        () => useInfiniteTrigs({ lat: 51.5, lon: -0.1 }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });
  });
});

