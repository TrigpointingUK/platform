import React, { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../src/contexts/ThemeContext';

interface WrapperOptions {
  initialEntries?: string[];
}

/**
 * Creates a test wrapper with all the necessary providers.
 * Use this for rendering components that need routing, query client, and theme context.
 */
export function createTestWrapper(options: WrapperOptions = {}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  const Router = options.initialEntries ? MemoryRouter : BrowserRouter;
  const routerProps = options.initialEntries ? { initialEntries: options.initialEntries } : {};

  return ({ children }: { children: ReactNode }) => (
    <ThemeProvider>
      <Router {...routerProps}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </Router>
    </ThemeProvider>
  );
}

/**
 * Creates a minimal wrapper with just the ThemeProvider.
 * Use this for testing components that only need theme context.
 */
export function createThemeWrapper() {
  return ({ children }: { children: ReactNode }) => (
    <ThemeProvider>
      {children}
    </ThemeProvider>
  );
}
