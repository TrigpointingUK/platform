# Frontend Testing Implementation

## Overview
Comprehensive testing suite for the TrigpointingUK web frontend using Vitest and React Testing Library.

## Test Coverage

### Current Status
✅ **80 tests passing**  
✅ **All critical components covered**  
📊 **Coverage Summary:**
- Overall: 45.68% statements
- Key areas with excellent coverage:
  - UI Components: 100%
  - photoHistory utility: 96.11%
  - useInfinitePhotos hook: 96.77%
  - LogCard component: 100%
  - PhotoGrid component: 100%
  - PhotoAlbum route: 91.7%

## Test Suite Structure

### 1. Utility Tests (`src/lib/__tests__/`)
**photoHistory.test.ts** - 18 tests
- localStorage operations
- Range merging logic
- Photo viewed detection
- History statistics
- Error handling (corrupted data, storage failures)

### 2. Hook Tests (`src/hooks/__tests__/`)
**useInfinitePhotos.test.tsx** - 6 tests
- Photo fetching with React Query
- Unseen/all mode filtering
- API URL construction
- Error handling
- Query key differentiation

### 3. UI Component Tests (`src/components/ui/__tests__/`)
**Button.test.tsx** - 9 tests
- Rendering with different variants (primary, secondary, ghost)
- Click handlers
- Disabled state
- Custom classNames

**Card.test.tsx** - 4 tests
- Children rendering
- Default classes
- Custom styling

**Badge.test.tsx** - 8 tests
- All variants (good, damaged, missing, unknown, default)
- Styling consistency

### 4. Smart Component Tests (`src/components/`)
**LogCard.test.tsx** - 14 tests
- TP format rendering (TP12345)
- Score display (out of 10)
- Condition badges
- Date/time formatting
- Photo rendering
- Links to trig and user pages

**PhotoGrid.test.tsx** - 7 tests
- Photo rendering
- Empty states
- Click handlers
- Grid layout
- Error scenarios

### 5. Integration Tests (`src/routes/__tests__/`)
**PhotoAlbum.test.tsx** - 13 tests
- Full page rendering with Layout
- Loading states
- Toggle between Unseen/All photos
- History management (reset functionality)
- Error states
- Empty states
- Confirmation dialogs

## Running Tests

### Commands
```bash
# Watch mode (default) - reruns on file changes
npm test

# Run once
npm run test:run

# With coverage report
npm run test:coverage

# With UI (if @vitest/ui installed)
npm run test:ui
```

### Configuration
Test configuration in `vite.config.ts`:
- Environment: jsdom (for DOM simulation)
- Globals: enabled (describe, it, expect available globally)
- Setup file: `tests/setup.ts`
- Coverage provider: v8

## Test Setup (`tests/setup.ts`)
- React Testing Library cleanup after each test
- Mock environment variables (VITE_API_BASE)
- Mock window.matchMedia for CSS-in-JS
- Mock IntersectionObserver for infinite scroll

## Testing Patterns

### Mocking
```typescript
// Mock modules
vi.mock('../../lib/photoHistory', () => ({
  getViewedRanges: vi.fn(() => []),
  addViewedRange: vi.fn(),
}));

// Mock fetch
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ items: [], total: 0 }),
});
```

### Testing Components with React Query
```typescript
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);

renderHook(() => useInfinitePhotos(), { wrapper });
```

### Testing Components with React Router
```typescript
const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};
```

## What's NOT Tested (Yet)
These components lack test coverage but aren't critical for current functionality:
- `main.tsx`, `router.tsx` (application bootstrap)
- `Header.tsx` sidebar logic
- `Sidebar.tsx` (mobile navigation)
- `LogList.tsx` (simple wrapper)
- Other route components (Home, About, etc.)
- Remaining hooks (useNews, useRecentLogs, useSiteStats)
- API/auth utilities

## CI/CD Integration

### Recommended Makefile targets
```makefile
.PHONY: test-web
test-web:
	cd web && npm run test:run

.PHONY: test-web-coverage
test-web-coverage:
	cd web && npm run test:coverage

# Update existing ci target
ci: lint test test-web type-check
```

### GitHub Actions (if applicable)
```yaml
- name: Run frontend tests
  run: |
    cd web
    npm ci
    npm run test:run
    npm run test:coverage
```

## Best Practices Followed
1. ✅ Test user behavior, not implementation details
2. ✅ Use semantic queries (getByRole, getByText)
3. ✅ Mock external dependencies (API calls, localStorage)
4. ✅ Test error states and edge cases
5. ✅ Keep tests focused and readable
6. ✅ Use descriptive test names
7. ✅ Clean up after tests (via setup.ts)

## Future Improvements
- [ ] Increase coverage of route components
- [ ] Add tests for remaining hooks
- [ ] Test Auth0 integration flows
- [ ] Add visual regression testing (optional)
- [ ] Performance testing for large photo lists
- [ ] Accessibility testing (jest-axe)

## Dependencies
- **vitest**: Jest-compatible test runner for Vite
- **@testing-library/react**: Component testing utilities
- **@testing-library/jest-dom**: Custom matchers (toBeInTheDocument, etc.)
- **@testing-library/user-event**: Simulate user interactions
- **jsdom**: DOM implementation for Node.js
- **@vitest/coverage-v8**: Coverage reporting

## Resources
- [Vitest Docs](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Library Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

