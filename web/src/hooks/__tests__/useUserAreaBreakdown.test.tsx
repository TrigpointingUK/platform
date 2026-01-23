import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUserAreaBreakdown } from '../useUserAreaBreakdown';
import { ReactNode } from 'react';

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

const mockBreakdownResponse = {
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

describe('useUserAreaBreakdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe('basic functionality', () => {
    it('should not fetch when userId is undefined', async () => {
      const { result } = renderHook(
        () => useUserAreaBreakdown(undefined, 'county_1991'),
        { wrapper: createWrapper() }
      );

      // Should not be fetching
      expect(result.current.isFetching).toBe(false);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should fetch when userId is provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBreakdownResponse,
      } as Response);

      const { result } = renderHook(
        () => useUserAreaBreakdown(123, 'county_1991'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('/v1/users/123/area-breakdown');
      expect(callUrl).toContain('area_type_code=county_1991');
    });

    it('should use default area type code when not specified', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBreakdownResponse,
      } as Response);

      renderHook(() => useUserAreaBreakdown(123), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('/v1/users/123/area-breakdown');
      expect(callUrl).toContain('area_type_code=county_1991');
    });

    it('should return breakdown data', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBreakdownResponse,
      } as Response);

      const { result } = renderHook(
        () => useUserAreaBreakdown(123, 'county_1991'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.area_type.code).toBe('county_1991');
      expect(result.current.data?.area_type.description).toBe(
        'Counties as defined in 1991'
      );
      expect(result.current.data?.items).toHaveLength(3);
      expect(result.current.data?.items[0].area_name).toBe('Greater London');
      expect(result.current.data?.items[0].count).toBe(15);
    });

    it('should handle string userId', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBreakdownResponse,
      } as Response);

      renderHook(() => useUserAreaBreakdown('456', 'historic_county'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('/v1/users/456/area-breakdown');
      expect(callUrl).toContain('area_type_code=historic_county');
    });
  });

  describe('different area types', () => {
    it('should fetch with custom area type code', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          area_type: {
            id: 2,
            code: 'historic_county',
            name: 'Historic County',
            description: 'Traditional historic counties',
          },
          items: [{ area_name: 'Yorkshire', count: 10 }],
        }),
      } as Response);

      const { result } = renderHook(
        () => useUserAreaBreakdown(123, 'historic_county'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.area_type.code).toBe('historic_county');
    });

    it('should encode special characters in area type code', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockBreakdownResponse,
      } as Response);

      renderHook(() => useUserAreaBreakdown(123, 'os_landranger'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('/v1/users/123/area-breakdown');
      expect(callUrl).toContain('area_type_code=os_landranger');
    });
  });

  describe('error handling', () => {
    it('should handle fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      } as Response);

      const { result } = renderHook(
        () => useUserAreaBreakdown(123, 'nonexistent'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(
        () => useUserAreaBreakdown(123, 'county_1991'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error?.message).toBe('Network error');
    });
  });

  describe('query key changes', () => {
    it('should refetch when area type code changes', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockBreakdownResponse,
      } as Response);

      const { rerender } = renderHook(
        ({ areaTypeCode }) => useUserAreaBreakdown(123, areaTypeCode),
        {
          wrapper: createWrapper(),
          initialProps: { areaTypeCode: 'county_1991' },
        }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

      // Change area type code
      rerender({ areaTypeCode: 'historic_county' });

      await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));

      const lastCall = mockFetch.mock.calls[1][0] as string;
      expect(lastCall).toContain('/v1/users/123/area-breakdown');
      expect(lastCall).toContain('area_type_code=historic_county');
    });

    it('should refetch when userId changes', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockBreakdownResponse,
      } as Response);

      const { rerender } = renderHook(
        ({ userId }) => useUserAreaBreakdown(userId, 'county_1991'),
        {
          wrapper: createWrapper(),
          initialProps: { userId: 123 as number | undefined },
        }
      );

      await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

      // Change user ID
      rerender({ userId: 456 });

      await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));

      const lastCall = mockFetch.mock.calls[1][0] as string;
      expect(lastCall).toContain('/v1/users/456/area-breakdown');
      expect(lastCall).toContain('area_type_code=county_1991');
    });
  });

  describe('empty results', () => {
    it('should handle empty items array', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          area_type: {
            id: 1,
            code: 'county_1991',
            name: 'County (1991)',
            description: null,
          },
          items: [],
        }),
      } as Response);

      const { result } = renderHook(
        () => useUserAreaBreakdown(123, 'county_1991'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.items).toHaveLength(0);
    });
  });
});

