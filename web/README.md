# TrigpointingUK - Web Application

Modern React single-page application (SPA) for TrigpointingUK, built with Vite, TypeScript, and Auth0 authentication.

## Architecture

The web application is deployed as an ECS Fargate service running nginx to serve the built React application. It uses:

- **React 18** with TypeScript
- **Vite** for fast builds and development
- **Tailwind CSS v4** for styling with custom TrigpointingUK green palette
- **Auth0** for authentication (PKCE flow with refresh tokens)
- **TanStack Query** for server state management and caching
- **React Router** for client-side routing
- **react-intersection-observer** for infinite scrolling
- **nginx** for production serving with SPA routing support

## Local Development

### Prerequisites

- Node.js 20.x or later
- npm (comes with Node.js)

### Setup

1. Install dependencies:
```bash
npm ci
```

2. Create `.env` file from example:
```bash
cp .env.example .env
```

3. Update `.env` with your Auth0 credentials:
   - Get `VITE_AUTH0_CLIENT_ID` from Terraform output: `terraform output -raw auth0_web_spa_client_id`
   - For local development, use staging values (trigpointing.me)

4. Ensure Auth0 has `http://localhost:5173` added to:
   - Allowed Callback URLs
   - Allowed Logout URLs
   - Allowed Web Origins

### Development Server

```bash
npm run dev
```

Or using the Makefile from the project root:
```bash
make web-dev
```

The application will be available at `http://localhost:5173`.

### Building

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Testing

```bash
npm test          # Run tests
npm run lint      # Lint code
npm run type-check # Type check
```

Or from project root:
```bash
make web-test
make web-lint
make web-type-check
```

## Deployment

The web application is automatically deployed via GitHub Actions:

- **Staging**: Pushes to `develop` branch deploy to staging (trigpointing.me/app/*)
- **Production**: Pushes to `main` branch deploy to production (trigpointing.uk/app/*)

### Deployment Process

1. GitHub Actions builds the Docker image with environment-specific build args
2. Image is pushed to GitHub Container Registry (ghcr.io/trigpointinguk/web)
3. ECS service is updated with the new image
4. ECS pulls the image and performs a rolling deployment

### Infrastructure

Terraform configuration:
- `terraform/modules/spa-ecs-service/` - ECS service module
- `terraform/staging/spa.tf` - Staging configuration
- `terraform/production/spa.tf` - Production configuration

## Project Structure

```
web/
├── public/
│   ├── TUK-Logo.svg       # Site logo
│   └── news.json          # Static news items (editable)
├── src/
│   ├── components/
│   │   ├── layout/        # Header, Footer, Sidebar, Layout
│   │   ├── ui/            # Button, Card, Badge, StarRating, Spinner
│   │   ├── logs/          # LogCard, LogList
│   │   └── photos/        # PhotoThumbnail, PhotoGrid
│   ├── hooks/             # Custom React Query hooks
│   │   ├── useSiteStats.ts
│   │   ├── useRecentLogs.ts
│   │   ├── useInfinitePhotos.ts
│   │   └── useNews.ts
│   ├── lib/               # Utilities (auth, api client)
│   ├── routes/            # Page components
│   │   ├── Home.tsx       # Homepage with stats, news, recent logs
│   │   ├── PhotoAlbum.tsx # Infinite scrolling photo gallery
│   │   ├── AppDetail.tsx
│   │   └── NotFound.tsx
│   ├── main.tsx           # Application entry point
│   ├── router.tsx         # Route configuration
│   └── app.css            # Tailwind directives
├── tests/                 # Test files
├── tailwind.config.js     # Tailwind configuration with custom colors
├── postcss.config.js      # PostCSS with Tailwind v4 plugin
├── Dockerfile             # Multi-stage build (Node + nginx)
├── nginx.conf             # nginx configuration for SPA
├── IMPLEMENTATION_SUMMARY.md  # Detailed implementation notes
├── COMPONENT_GUIDE.md     # Component usage documentation
└── package.json           # Dependencies and scripts
```

See `COMPONENT_GUIDE.md` for detailed component usage and examples.

## Authentication

The application uses Auth0 with PKCE (Proof Key for Code Exchange) flow:

- Tokens are stored in memory (not localStorage)
- Refresh tokens are automatically used for token renewal
- No cookies - uses Bearer tokens for API requests
- Tokens included in `Authorization: Bearer <token>` header

### Using the Auth Hook

```typescript
import { useAccessToken } from './lib/auth';
import { apiGet } from './lib/api';

function MyComponent() {
  const { getToken } = useAccessToken();
  
  const { data } = useQuery({
    queryKey: ['myData'],
    queryFn: async () => {
      const token = await getToken();
      return apiGet('/v1/my-endpoint', token);
    }
  });
}
```

## API Integration

The application communicates with the FastAPI backend at:
- Staging: `https://api.trigpointing.me`
- Production: `https://api.trigpointing.uk`

CORS is configured to allow the SPA origin with Bearer tokens (no credentials).

## Routing Strategy

The application uses infrastructure-level routing via ALB:

### Current Setup (Initial Testing)
- `/app/*` routes to the SPA ECS service
- All other routes go to legacy services

### Future Migration Path
As features are implemented and tested:
1. Update ALB listener rules to route specific paths to SPA
2. Add CloudFlare redirects for old URLs (e.g., `/info/view-profile.php?u=123` → `/user/123`)
3. Gradually expand SPA coverage

Example migration:
```hcl
# Once /user/:id is fully implemented and tested
path_patterns = ["/app/*", "/user/*"]
```

## Strangler Fig Pattern

This web application follows the "strangler fig" pattern to gradually replace legacy PHP pages:

1. **Phase 1**: Deploy SPA at `/app/*` for testing
2. **Phase 2**: Implement specific features (e.g., user profiles)
3. **Phase 3**: Move ALB routes from legacy to SPA one feature at a time
4. **Phase 4**: Eventually replace all pages

This allows:
- Zero-downtime migration
- Feature-by-feature rollout
- Easy rollback if needed
- Parallel operation of old and new

## Environment Variables

### Build-Time (Vite)
- `VITE_AUTH0_DOMAIN` - Auth0 custom domain
- `VITE_AUTH0_CLIENT_ID` - Auth0 SPA client ID
- `VITE_AUTH0_AUDIENCE` - Auth0 API audience
- `VITE_API_BASE` - API base URL

### nginx Runtime
No runtime environment variables - all config is baked into the build.

## Security

- Content Security Policy (CSP) headers in `index.html`
- Auth0 tokens in memory (not localStorage)
- HTTPS only in production
- CloudFlare WAF and DDoS protection
- Security headers added by nginx

## Performance

- Vite for fast builds and HMR
- Code splitting with React lazy loading
- Aggressive caching for assets (1 year)
- No caching for `index.html`
- Gzip compression enabled in nginx

## Troubleshooting

### Auth0 Login Redirect Loop
- Check that callback URL is in Auth0 allowed list
- Verify `VITE_AUTH0_CLIENT_ID` matches Auth0 application
- Check browser console for errors

### API Requests Failing
- Verify CORS origins in API configuration
- Check that token is included in request headers
- Ensure API is accessible from SPA origin

### Build Errors
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm ci`
- Check Node version: `node --version` (should be 20.x)
- Verify all environment variables are set

## Contributing

1. Create feature branch from `develop`
2. Make changes and test locally
3. Run `make web-lint web-type-check web-test` to verify
4. Push to GitHub and create PR
5. Once merged to `develop`, deploy to staging automatically
6. After testing in staging, merge to `main` for production

## Links

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [Auth0 React SDK](https://auth0.com/docs/libraries/auth0-react)
- [TanStack Query](https://tanstack.com/query/latest)
- [React Router](https://reactrouter.com/)

