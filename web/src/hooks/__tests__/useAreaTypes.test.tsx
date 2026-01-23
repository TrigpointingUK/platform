import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAreaTypes } from '../useAreaTypes';
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

const mockAreaTypesResponse = [
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
  {
    id: 3,
    code: 'os_landranger',
    name: 'OS Landranger Map',
    description: null,
  },
];

describe('useAreaTypes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe('basic functionality', () => {
    it('should fetch area types on mount', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAreaTypesResponse,
      } as Response);

      const { result } = renderHook(() => useAreaTypes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('/v1/areas/types');
    });

    it('should return area types data', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAreaTypesResponse,
      } as Response);

      const { result } = renderHook(() => useAreaTypes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(3);
      expect(result.current.data?.[0].code).toBe('county_1991');
      expect(result.current.data?.[0].description).toBe(
        'Counties as defined in 1991'
      );
    });

    it('should handle null description', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAreaTypesResponse,
      } as Response);

      const { result } = renderHook(() => useAreaTypes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const osLandranger = result.current.data?.find(
        (t) => t.code === 'os_landranger'
      );
      expect(osLandranger?.description).toBeNull();
    });
  });

  describe('error handling', () => {
    it('should handle fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response);

      const { result } = renderHook(() => useAreaTypes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useAreaTypes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error?.message).toBe('Network error');
    });
  });

  describe('caching', () => {
    it('should have a long stale time for caching', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAreaTypesResponse,
      } as Response);

      const { result } = renderHook(() => useAreaTypes(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Data should be considered fresh (not stale immediately)
      expect(result.current.isStale).toBe(false);
    });
  });
});

