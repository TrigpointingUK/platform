import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '../../contexts/ThemeProvider';
import LogDetail from '../LogDetail';
import { useLogDetail } from '../../hooks/useLogDetail';
import { useTrigDetail } from '../../hooks/useTrigDetail';
import { useCurrentUser } from '../../hooks/useCurrentUser';
import { useUserProfile } from '../../hooks/useUserProfile';
import { useAuth0 } from '@auth0/auth0-react';

// Mock hooks
vi.mock('@auth0/auth0-react', () => ({
  useAuth0: vi.fn(),
}));

vi.mock('../../hooks/useLogDetail', () => ({
  useLogDetail: vi.fn(),
}));

vi.mock('../../hooks/useTrigDetail', () => ({
  useTrigDetail: vi.fn(),
}));

vi.mock('../../hooks/useCurrentUser', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('../../hooks/useUserProfile', () => ({
  useUserProfile: vi.fn(),
}));

vi.mock('../../hooks/useUpdateLog', () => ({
  useUpdateLog: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}));

vi.mock('../../hooks/useDeleteLog', () => ({
  useDeleteLog: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}));

vi.mock('../../hooks/useAreasContaining', () => ({
  useAreasContaining: vi.fn(() => ({
    data: { groups: [] },
    isLoading: false,
  })),
}));

vi.mock('../../components/layout/GlobalSearch', () => ({
  GlobalSearch: () => <div data-testid="global-search" />,
}));

const mockUseAuth0 = vi.mocked(useAuth0);
const mockUseLogDetail = vi.mocked(useLogDetail);
const mockUseTrigDetail = vi.mocked(useTrigDetail);
const mockUseCurrentUser = vi.mocked(useCurrentUser);
const mockUseUserProfile = vi.mocked(useUserProfile);

const mockLog = {
  id: 123,
  trig_id: 456,
  user_id: 100,
  trig_name: 'Test Hill',
  user_name: 'Test User',
  date: '2024-01-15',
  time: '14:30',
  condition: 'G',
  comment: 'A great visit',
  score: 8,
  osgb_gridref: 'TQ123456',
  osgb_eastings: 512345,
  osgb_northings: 134567,
  fb_number: 'S1234',
  source: 'web',
};

const mockTrig = {
  id: 456,
  waypoint: 'TP0456',
  name: 'Test Hill',
  condition: 'G',
  wgs_lat: 51.5074,
  wgs_long: -0.1278,
  osgb_gridref: 'TQ123456',
  grid_system: 'gb' as const,
  type_code: 'HOTINE',
  type_name: 'Hotine Pillar',
  category_code: 'PILLAR',
  category_name: 'Pillar',
  details: {
    osgb_height: 100,
    postcode: 'SW1A 1AA',
    current_use: 'None',
    historic_use: 'Triangulation',
    county: 'Test County',
    town: 'Test Town',
    fb_number: 'S1234',
    stn_number_active: '',
    stn_number_passive: 'P123456',
    stn_number_osgb36: '',
    legal_message: null,
  },
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithProviders = (logId: string = '123') => {
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter initialEntries={[`/logs/${logId}`]}>
          <Routes>
            <Route path="/logs/:logId" element={<LogDetail />} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('LogDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();

    mockUseAuth0.mockReturnValue({
      isAuthenticated: false,
      user: undefined,
      isLoading: false,
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      getAccessTokenSilently: vi.fn(),
    } as never);

    mockUseCurrentUser.mockReturnValue({
      data: null,
      isLoading: false,
    } as never);

    mockUseUserProfile.mockReturnValue({
      data: null,
      isLoading: false,
    } as never);
  });

  it('should show loading state initially', () => {
    mockUseLogDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as never);

    renderWithProviders();

    expect(screen.getByText(/Loading log/i)).toBeInTheDocument();
  });

  it('should show error state when log fails to load', () => {
    mockUseLogDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load'),
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as never);

    renderWithProviders();

    expect(screen.getByText(/Failed to load log details/i)).toBeInTheDocument();
  });

  it('should show not found when log does not exist', () => {
    mockUseLogDetail.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as never);

    renderWithProviders();

    expect(screen.getByText(/Log not found/i)).toBeInTheDocument();
  });

  it('should render log details and trig info section when loaded', async () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    renderWithProviders();

    // Wait for content to load
    await waitFor(() => {
      // Check that the TrigInfoSection is rendered
      expect(screen.getByText('TP0456 - Test Hill')).toBeInTheDocument();
    });

    // Check that basic trig info is shown
    expect(screen.getByText('TQ123456')).toBeInTheDocument();
    expect(screen.getByText('51.5074000, -0.1278000')).toBeInTheDocument();
    
    // Check that log card content is rendered
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('A great visit')).toBeInTheDocument();
  });

  it('should show loading state when trig is still loading', () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as never);

    renderWithProviders();

    expect(screen.getByText(/Loading log/i)).toBeInTheDocument();
  });

  it('should render back button', async () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Back/i })).toBeInTheDocument();
    });
  });

  it('should not show edit/delete buttons when user is not owner', async () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    mockUseCurrentUser.mockReturnValue({
      data: { id: 999, name: 'Other User' }, // Different user
      isLoading: false,
    } as never);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('TP0456 - Test Hill')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /Edit Log/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Delete Log/i })).not.toBeInTheDocument();
  });

  it('should show edit/delete buttons when user is owner', async () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    mockUseCurrentUser.mockReturnValue({
      data: { id: 100, name: 'Test User' }, // Same as log user_id
      isLoading: false,
    } as never);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Edit Log/i })).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Delete Log/i })).toBeInTheDocument();
  });

  it('should render trig info even when details are loaded', async () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    renderWithProviders();

    await waitFor(() => {
      // Check TrigInfoSection elements
      expect(screen.getByText('TP0456 - Test Hill')).toBeInTheDocument();
      expect(screen.getByText(/Grid reference:/i)).toBeInTheDocument();
      expect(screen.getByText(/WGS coordinates:/i)).toBeInTheDocument();
      expect(screen.getByText(/Height above sea level:/i)).toBeInTheDocument();
      expect(screen.getByText('100.000m')).toBeInTheDocument();
    });
  });

  it('should show links to map and photo album in trig info section', async () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /View on Interactive Map/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /View Photo Album/i })).toBeInTheDocument();
    });
  });

  it('should show invalid log ID error for invalid path', () => {
    mockUseLogDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as never);

    // Render with invalid log ID
    render(
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <MemoryRouter initialEntries={['/logs/invalid']}>
            <Routes>
              <Route path="/logs/:logId" element={<LogDetail />} />
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>
    );

    // NaN conversion shows "Invalid log ID" error
    expect(screen.getByText(/Invalid log ID/i)).toBeInTheDocument();
  });

  it('should show Facebook share button inside log card via showShareButton', async () => {
    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('TP0456 - Test Hill')).toBeInTheDocument();
    });

    // Facebook share button for the log should be in the card
    const shareButtons = screen.getAllByTitle('Share on Facebook');
    expect(shareButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('should not render AddToListButton in breadcrumb area', async () => {
    mockUseAuth0.mockReturnValue({
      isAuthenticated: true,
      user: { sub: 'auth0|123' },
      isLoading: false,
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      getAccessTokenSilently: vi.fn(),
    } as never);

    mockUseLogDetail.mockReturnValue({
      data: mockLog,
      isLoading: false,
      error: null,
    } as never);

    mockUseTrigDetail.mockReturnValue({
      data: mockTrig,
      isLoading: false,
    } as never);

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText('TP0456 - Test Hill')).toBeInTheDocument();
    });

    // The Back button should be alone in the breadcrumb
    const backButton = screen.getByRole('button', { name: /Back/i });
    const breadcrumb = backButton.parentElement!;
    // AddToListButton renders buttons with title "Add to default list" or "Add to other lists"
    // These should NOT be direct children of the breadcrumb
    const listButtons = breadcrumb.querySelectorAll('[title*="list"]');
    expect(listButtons.length).toBe(0);
  });
});

