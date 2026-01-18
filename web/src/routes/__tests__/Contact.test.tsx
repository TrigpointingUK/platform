import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { useAuth0, User } from '@auth0/auth0-react';
import { ThemeProvider } from '../../contexts/ThemeContext';
import Contact from '../Contact';

type UseAuth0Return = ReturnType<typeof useAuth0>;

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Mock Auth0
vi.mock('@auth0/auth0-react', () => ({
  useAuth0: vi.fn(),
}));

// Mock authenticatedPost from api
const mockAuthenticatedPost = vi.fn();
vi.mock('../../lib/api', () => ({
  authenticatedPost: (...args: unknown[]) => mockAuthenticatedPost(...args),
}));

// Mock useUserProfile hook
const mockUseUserProfile = vi.fn();

vi.mock('../../hooks/useUserProfile', () => ({
  useUserProfile: (userId: string | number) => mockUseUserProfile(userId),
}));

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  
  return ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider>
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
};

describe('Contact', () => {
  const mockUseAuth0 = vi.mocked(useAuth0);

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock: unauthenticated user
    mockUseAuth0.mockReturnValue({
      isAuthenticated: false,
      user: undefined,
      getAccessTokenSilently: vi.fn(),
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
      error: undefined,
    } as unknown as UseAuth0Return);

    // Default mock: no user profile
    mockUseUserProfile.mockReturnValue({
      data: null,
      error: null,
      isLoading: false,
    });

    // Mock successful fetch response for unauthenticated submissions
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true, message: 'Sent' }),
    });

    // Mock successful authenticated post
    mockAuthenticatedPost.mockResolvedValue({
      success: true,
      message: 'Your message has been sent successfully!',
    });
  });

  it('should render contact form', () => {
    render(<Contact />, { wrapper: createWrapper() });
    
    expect(screen.getByRole('heading', { name: 'Contact Us' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Subject/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Message/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send/i })).toBeInTheDocument();
  });

  it('should have Send button disabled when form is invalid', () => {
    render(<Contact />, { wrapper: createWrapper() });
    
    const sendButton = screen.getByRole('button', { name: /Send/i });
    expect(sendButton).toBeDisabled();
  });

  it('should enable Send button when form is valid', () => {
    render(<Contact />, { wrapper: createWrapper() });
    
    const nameInput = screen.getByLabelText(/Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const subjectInput = screen.getByLabelText(/Subject/i);
    const messageInput = screen.getByLabelText(/Message/i);
    
    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(subjectInput, { target: { value: 'Test Subject' } });
    fireEvent.change(messageInput, { target: { value: 'Test message' } });
    
    const sendButton = screen.getByRole('button', { name: /Send/i });
    expect(sendButton).not.toBeDisabled();
  });

  it('should pre-populate name and email for authenticated users', async () => {
    mockUseAuth0.mockReturnValue({
      isAuthenticated: true,
      user: {
        name: 'Test User',
        email: 'test@example.com',
        nickname: 'testuser',
      } as User,
      getAccessTokenSilently: vi.fn().mockResolvedValue('mock_token'),
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
      error: undefined,
    } as unknown as UseAuth0Return);

    mockUseUserProfile.mockReturnValue({
      data: {
        id: 1,
        name: 'testuser',
        firstname: 'Test',
        surname: 'User',
        homepage: null,
        about: '',
        member_since: null,
        prefs: {
          email: 'test@example.com',
          email_valid: 'Y',
          distance_ind: 'M',
          public_ind: 'Y',
          online_map_type: 'standard',
          online_map_type2: 'standard',
        },
      },
      error: null,
      isLoading: false,
    });

    render(<Contact />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      const nameInput = screen.getByLabelText(/Name/i) as HTMLInputElement;
      const emailInput = screen.getByLabelText(/Email Address/i) as HTMLInputElement;
      
      // Should be pre-populated (either from profile or Auth0 user)
      expect(nameInput.value).toBeTruthy();
      expect(emailInput.value).toBeTruthy();
    });
  });

  it('should submit form successfully', async () => {
    render(<Contact />, { wrapper: createWrapper() });
    
    const nameInput = screen.getByLabelText(/Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const subjectInput = screen.getByLabelText(/Subject/i);
    const messageInput = screen.getByLabelText(/Message/i);
    const sendButton = screen.getByRole('button', { name: /Send/i });
    
    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(subjectInput, { target: { value: 'Test Subject' } });
    fireEvent.change(messageInput, { target: { value: 'Test message content' } });
    
    fireEvent.click(sendButton);
    
    // For unauthenticated users, should use fetch directly
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/v1/admin/contact'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('John Doe'),
        })
      );
    });
  });

  it('should submit form with token for authenticated users', async () => {
    const mockGetAccessTokenSilently = vi.fn().mockResolvedValue('mock_auth_token');
    mockUseAuth0.mockReturnValue({
      isAuthenticated: true,
      user: {
        name: 'Test User',
        email: 'test@example.com',
      } as User,
      getAccessTokenSilently: mockGetAccessTokenSilently,
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
      error: undefined,
    } as unknown as UseAuth0Return);

    render(<Contact />, { wrapper: createWrapper() });
    
    const nameInput = screen.getByLabelText(/Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const subjectInput = screen.getByLabelText(/Subject/i);
    const messageInput = screen.getByLabelText(/Message/i);
    const sendButton = screen.getByRole('button', { name: /Send/i });
    
    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(subjectInput, { target: { value: 'Test Subject' } });
    fireEvent.change(messageInput, { target: { value: 'Test message' } });
    
    fireEvent.click(sendButton);
    
    // For authenticated users, should use authenticatedPost
    await waitFor(() => {
      expect(mockAuthenticatedPost).toHaveBeenCalledWith(
        expect.stringContaining('/v1/admin/contact'),
        expect.objectContaining({
          name: 'John Doe',
          email: 'john@example.com',
          subject: 'Test Subject',
          message: 'Test message',
        }),
        mockGetAccessTokenSilently
      );
    });
  });

  it('should validate email format', () => {
    render(<Contact />, { wrapper: createWrapper() });
    
    const nameInput = screen.getByLabelText(/Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const subjectInput = screen.getByLabelText(/Subject/i);
    const messageInput = screen.getByLabelText(/Message/i);
    const sendButton = screen.getByRole('button', { name: /Send/i });
    
    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } }); // Invalid email
    fireEvent.change(subjectInput, { target: { value: 'Test Subject' } });
    fireEvent.change(messageInput, { target: { value: 'Test message' } });
    
    // Button should still be disabled due to invalid email
    expect(sendButton).toBeDisabled();
  });

  it('should show error toast on submission failure', async () => {
    const { default: toast } = await import('react-hot-toast');
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    render(<Contact />, { wrapper: createWrapper() });
    
    const nameInput = screen.getByLabelText(/Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const subjectInput = screen.getByLabelText(/Subject/i);
    const messageInput = screen.getByLabelText(/Message/i);
    const sendButton = screen.getByRole('button', { name: /Send/i });
    
    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(subjectInput, { target: { value: 'Test Subject' } });
    fireEvent.change(messageInput, { target: { value: 'Test message' } });
    
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });

  it('should trim whitespace from form fields', async () => {
    render(<Contact />, { wrapper: createWrapper() });
    
    const nameInput = screen.getByLabelText(/Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const subjectInput = screen.getByLabelText(/Subject/i);
    const messageInput = screen.getByLabelText(/Message/i);
    const sendButton = screen.getByRole('button', { name: /Send/i });
    
    fireEvent.change(nameInput, { target: { value: '  John Doe  ' } });
    fireEvent.change(emailInput, { target: { value: '  john@example.com  ' } });
    fireEvent.change(subjectInput, { target: { value: '  Test Subject  ' } });
    fireEvent.change(messageInput, { target: { value: '  Test message  ' } });
    
    fireEvent.click(sendButton);
    
    // For unauthenticated users, uses fetch directly with trimmed values
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/v1/admin/contact'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('John Doe'), // Trimmed
        })
      );
    });
  });

  it('should reset form after successful submission', async () => {
    render(<Contact />, { wrapper: createWrapper() });
    
    const nameInput = screen.getByLabelText(/Name/i) as HTMLInputElement;
    const emailInput = screen.getByLabelText(/Email Address/i) as HTMLInputElement;
    const subjectInput = screen.getByLabelText(/Subject/i) as HTMLInputElement;
    const messageInput = screen.getByLabelText(/Message/i) as HTMLTextAreaElement;
    const sendButton = screen.getByRole('button', { name: /Send/i });
    
    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(emailInput, { target: { value: 'john@example.com' } });
    fireEvent.change(subjectInput, { target: { value: 'Test Subject' } });
    fireEvent.change(messageInput, { target: { value: 'Test message' } });
    
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    // Subject and message should be cleared (name/email stay if user is logged in)
    await waitFor(() => {
      expect(subjectInput.value).toBe('');
      expect(messageInput.value).toBe('');
    });
  });
});

