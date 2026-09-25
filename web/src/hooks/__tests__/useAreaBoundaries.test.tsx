import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAreaBoundaries } from '../useAreaBoundary';
import { ReactNode } from 'react';

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

vi.stubEnv('VITE_API_BASE', 'http://localhost:8000');

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const boundaryFor = (id: number) => ({
  id,
  name: `Area ${id}`,
  code: null,
  area_type: { id: 1, code: 'county_1991', name: 'County (1991)' },
  boundary: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] },
});

describe('useAreaBoundaries', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('returns nothing and makes no requests for no areas', () => {
    const { result } = renderHook(() => useAreaBoundaries([]), { wrapper: createWrapper() });
    expect(result.current).toEqual([]);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('fetches each area boundary separately', async () => {
    mockFetch.mockImplementation((url: string) => {
      const id = Number(url.match(/areas\/(\d+)\/boundary/)![1]);
      return Promise.resolve({ ok: true, json: async () => boundaryFor(id) });
    });

    const { result } = renderHook(() => useAreaBoundaries([3, 7]), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current).toHaveLength(2));
    expect(result.current.map((a) => a.id)).toEqual([3, 7]);
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/v1/areas/3/boundary');
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/v1/areas/7/boundary');
  });

  it('leaves out areas whose boundary fails to load', async () => {
    mockFetch.mockImplementation((url: string) =>
      Promise.resolve(
        url.includes('/areas/3/')
          ? { ok: true, json: async () => boundaryFor(3) }
          : { ok: false, status: 404 },
      ),
    );

    const { result } = renderHook(() => useAreaBoundaries([3, 7]), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current).toHaveLength(1));
    expect(result.current[0].id).toBe(3);
  });
});
