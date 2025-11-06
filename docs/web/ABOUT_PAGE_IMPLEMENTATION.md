# About Page Implementation

## What Was Created

Added a new `/about` page to the React web app that displays detailed build information including:
- Version number
- Git commit SHA and message
- Build timestamp
- GitHub Actions run information (when built in CI/CD)
- Technical details (Node version, environment)

## Files Created/Modified

### New Files:
1. **`web/generate-build-info.mjs`** - Node script that captures build metadata
   - Runs as `prebuild` step before `npm run build`
   - Captures git commit info, timestamps, GitHub Actions environment variables
   - Outputs to `web/public/buildInfo.json`

2. **`web/src/routes/About.tsx`** - About page component
   - Fetches buildInfo.json from public assets
   - Displays build info in organized cards
   - Shows git commit with link to GitHub
   - Shows GitHub Actions run info with link (when available)
   - Fully responsive with Tailwind styling

### Modified Files:
1. **`web/package.json`** - Added `prebuild` script
2. **`web/src/router.tsx`** - Added `/about` route
3. **`web/src/components/layout/Footer.tsx`** - Added "About" link
4. **`web/.gitignore`** - Ignore generated `public/buildInfo.json`

## How It Works

### Build Time:
```bash
npm run build
├── prebuild: node generate-build-info.mjs
│   └── Creates public/buildInfo.json with:
│       - Git commit SHA (full & short)
│       - Branch name
│       - Commit message
│       - Build timestamp
│       - Node version
│       - GitHub Actions metadata (if available)
│       - Environment (from VITE_ENVIRONMENT)
├── TypeScript compilation
└── Vite build
    └── Copies public/buildInfo.json to dist/
```

### Runtime:
1. User navigates to `/about`
2. About component fetches `/buildInfo.json`
3. Displays information in organized cards
4. Links to GitHub commit and Actions run (if available)

## GitHub Actions Integration

When built in GitHub Actions, the build info will include:
- `githubRun`: Run ID (links to the specific workflow run)
- `githubRunNumber`: Sequential run number
- `githubActor`: Who triggered the build
- `githubWorkflow`: Workflow name
- `githubRef`: Branch/tag reference

These are automatically captured from GitHub Actions environment variables.

## Example Build Info

### Local Development:
```json
{
  "version": "0.1.0",
  "commitSha": "b9e6dc6356991dbf3c9301b6ee14dcfdb0390e8e",
  "commitShort": "b9e6dc6",
  "branch": "develop",
  "commitMessage": "scaffolding web app",
  "buildTime": "2025-10-29T17:26:06.024Z",
  "nodeVersion": "v18.19.1",
  "githubRun": null,
  "githubRunNumber": null,
  "githubActor": null,
  "githubWorkflow": null,
  "githubRef": null,
  "environment": "development"
}
```

### GitHub Actions Build:
```json
{
  "version": "0.1.0",
  "commitSha": "b9e6dc6356991dbf3c9301b6ee14dcfdb0390e8e",
  "commitShort": "b9e6dc6",
  "branch": "develop",
  "commitMessage": "scaffolding web app",
  "buildTime": "2025-10-29T17:26:06.024Z",
  "nodeVersion": "v20.11.1",
  "githubRun": "12345678",
  "githubRunNumber": "42",
  "githubActor": "ianh",
  "githubWorkflow": "Web CI/CD Pipeline",
  "githubRef": "refs/heads/develop",
  "environment": "staging"
}
```

## Testing

### Test Locally:
```bash
cd /home/ianh/dev/platform/web
npm run dev
```

Navigate to: `http://localhost:5173/about`

### Test Build:
```bash
cd /home/ianh/dev/platform/web
npm run build
npm run preview
```

Navigate to: `http://localhost:4173/about`

## Features

1. **Responsive Design** - Works on mobile, tablet, and desktop
2. **GitHub Integration** - Links to commits and workflow runs
3. **Environment Badges** - Color-coded environment indicators
4. **Technical Details** - Node version, full commit SHA
5. **Build Timestamp** - Formatted in local timezone
6. **About Project** - Includes info about TrigpointingUK and tech stack

## Future Enhancements

Could be extended to include:
- API health status
- Database connection status
- Cache statistics
- Performance metrics
- Dependency versions
- Docker image information

## Commit and Deploy

The About page is now ready. When you commit and push:

```bash
git add .
git commit -m "Add About page with build information

- Create generate-build-info.mjs script
- Add /about route with detailed build info
- Display git commit, timestamp, GitHub Actions data
- Add About link to footer"

git push origin develop
```

After deployment to staging, visit:
- https://trigpointing.me/about

The build info will show the GitHub Actions run details!

## Repository Link

**Note:** Update the GitHub repository link in `About.tsx` if needed:
```typescript
const getGitHubLink = () => {
  if (!buildInfo?.commitSha) return null;
  // Update this URL to match your actual repository
  return `https://github.com/TrigpointingUK/platform/commit/${buildInfo.commitSha}`;
};
```

