import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LogResultItem } from '../LogResultItem';
import type { LogSearchResult } from '../../../../hooks/useSearchResults';

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('LogResultItem', () => {
  const baseItem: LogSearchResult = {
    id: 1,
    trig_id: 1234,
    trig_name: 'Whitchurch Hill',
    user_id: 100,
    user_name: 'surveyor',
    date: '2024-01-15',
    time: '14:30:00',
    condition: 'G',
    comment: 'Found it easily',
    score: 8,
  };

  it('shows category and type when they differ', () => {
    renderWithProviders(
      <LogResultItem
        item={{
          ...baseItem,
          trig_type_code: 'HOTINE',
          trig_type_name: 'Hotine Pillar',
          trig_category_code: 'PILLAR',
          trig_category_name: 'Pillar',
        }}
      />
    );

    expect(screen.getByText('Pillar · Hotine Pillar')).toBeInTheDocument();
  });

  it('shows only the type when it is the whole category', () => {
    renderWithProviders(
      <LogResultItem
        item={{
          ...baseItem,
          trig_type_code: 'FBM',
          trig_type_name: 'FBM',
          trig_category_code: 'FBM',
          trig_category_name: 'FBM',
        }}
      />
    );

    expect(screen.getByText('FBM')).toBeInTheDocument();
  });

  it('omits the type when the trig has none', () => {
    renderWithProviders(<LogResultItem item={baseItem} />);

    expect(screen.getByText('Whitchurch Hill')).toBeInTheDocument();
    expect(screen.queryByText(/Pillar/)).not.toBeInTheDocument();
  });
});
