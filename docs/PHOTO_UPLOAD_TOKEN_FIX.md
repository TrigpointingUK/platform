# Photo Upload Intermittent Failure Fix

**Date:** January 2026  
**Issue:** Users reporting that photo uploads only work on the second or third attempt

## Problem Description

Users reported intermittent failures when uploading photos to the website:

- Uploads typically succeed on the 2nd or 3rd attempt
- Issue appeared worse when adding photos to older logs
- Independent of photo size
- Independent of device type (PC/mobile) or connection (WiFi/4G)
- Could not be reproduced locally ("ItWorksOnMyMachine")

## Root Cause Analysis

After investigating the codebase, the most likely cause was identified as an **Auth0 token expiration race condition**.

### The Problem Flow

1. User navigates to a log and decides to upload a photo
2. Frontend calls `getAccessTokenSilently()` which returns a **cached token**
3. If that token is close to expiring (or has just expired by the time it reaches the server), the backend returns 401
4. The frontend's retry logic gets a **fresh token** and succeeds on retry

### Why "Worse for Old Logs"?

When users review or edit old logs before uploading photos, they tend to spend more time on the page. The longer they're on the page, the closer their cached token gets to expiration. By the time they click "Upload", the token may have already expired or be milliseconds from expiring.

### Technical Details

The photo upload flow involves:

```
Frontend: Get cached token → Send multipart POST with token
Backend: Validate token → Create DB record → Process image → Upload to S3 → Update DB
```

Token validation happens at the start of the request. If the token expired between the frontend retrieving it and the backend validating it (even by milliseconds due to network latency), the request fails.

The existing retry logic in `authenticatedFetch.ts` handles 401s by:
1. Forcing a token refresh (`cacheMode: 'off'`)
2. Retrying the request

However, for file uploads, this means re-uploading the entire file, which:
- Is wasteful and slow
- Could fail again if there's an underlying token timing issue
- Creates a poor user experience

## Solution Implemented

### Option 1: Force Fresh Token Before Upload (Implemented)

Modified `web/src/hooks/useLogPhotos.ts` to proactively request a fresh token before upload/rotate operations:

```typescript
// Force a fresh token for uploads to avoid near-expiry race conditions.
// File uploads are expensive to retry, so we proactively ensure we have
// a token with maximum remaining lifetime.
const freshToken = await getAccessTokenSilently({ cacheMode: "off" });
```

Applied to:
- `useUploadPhoto` - Photo uploads
- `useRotatePhoto` - Photo rotation (also involves server-side file processing)

### Option 2: Token Buffer in Auth0Provider (Not Applicable)

Investigation revealed that the Auth0 React SDK does **not** provide a built-in token buffer/expiry offset configuration. There is no:
- `cacheExpiryOffset`
- `tokenBufferSeconds`
- Any setting to "consider tokens expired N seconds early"

The `authorizeTimeoutInSeconds` property controls authorization request timeout, not token expiry buffer.

**Auth0's recommended approach** for critical operations is exactly what we implemented: explicitly requesting fresh tokens with `cacheMode: "off"`.

## Files Changed

- `web/src/hooks/useLogPhotos.ts`
  - `useUploadPhoto`: Now forces fresh token before upload
  - `useRotatePhoto`: Now forces fresh token before rotation
  - Removed unused imports (`authenticatedFetch`, `authenticatedPost`)

## Verification Steps

To verify this fix resolves the issue:

1. **Check CloudWatch Logs** for reduction in `auth0_token_validation_failed` with `expired_signature` reason:
   ```bash
   aws logs filter-log-events --log-group-name /ecs/fastapi-production \
     --filter-pattern '"auth0_token_validation_failed" "expired_signature"'
   ```

2. **Monitor 401 responses** on photo upload endpoints:
   ```bash
   aws logs filter-log-events --log-group-name /ecs/fastapi-production \
     --filter-pattern '"POST" "/v1/photos" "401"'
   ```

3. **User feedback** - The intermittent "upload fails on first attempt" should be resolved.

## Auth0 Configuration Context

Current Auth0 token settings:
- **Production API token lifetime:** 3600 seconds (1 hour) - default
- **Staging API token lifetime:** 120 seconds (2 minutes) - for testing token refresh
- **Refresh tokens:** Enabled (`useRefreshTokens`)
- **Refresh token fallback:** Enabled (`useRefreshTokensFallback`)
- **Cache location:** `localstorage`

## Best Practices Applied

This fix follows Auth0's recommended patterns:
1. ✅ Enable refresh tokens for automatic renewal
2. ✅ Use `useRefreshTokensFallback` for Safari/older browsers
3. ✅ Force fresh tokens (`cacheMode: "off"`) for critical operations where retrying is expensive

## Related Files

- `web/src/lib/authenticatedFetch.ts` - Contains the 401 retry logic
- `web/src/main.tsx` - Auth0Provider configuration
- `web/src/lib/auth.ts` - Centralised auth utilities with `useAuthToken` hook
- `api/core/security.py` - Backend token validation logic
- `api/api/v1/endpoints/photos.py` - Photo upload endpoint

