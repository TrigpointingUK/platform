# Admin Scope Step-Up Flow (Auth0)

This document explains how the SPA obtains the `api:admin` scope only after an explicit "step-up" through Auth0. It covers the intended behaviour, key configuration points, and troubleshooting guidance.

## Overview

Users with the `api-admin` role see an Admin menu item. When they visit `/admin`, the SPA checks the access token. If the token lacks the `api:admin` scope, the page forces an Auth0 re-authentication with consent so the user explicitly grants the extra permission. After returning, Auth0 supplies a refreshed access token containing the scope and the admin UI unlocks.

The flow is designed so that:

- The initial login remains lightweight (no unnecessary admin scope granted to every session).
- Admin scope acquisition is auditable and can be revoked by Auth0 policy.
- The SPA handles both staging (`trigpointing.me`) and production (`trigpointing.uk`) environments identically.

## Token Requests and Scopes

Both the global Auth0 provider (`web/src/main.tsx`) and the admin step-up request (`web/src/routes/Admin.tsx`) explicitly request the following baseline scopes:

```
openid profile email api:write api:read-pii offline_access
```

- `offline_access` is critical. Auth0 refuses to mint rotating refresh tokens without it, which previously resulted in `_g: Missing Refresh Token` errors and an infinite redirect loop.
- The admin step-up adds `api:admin` to the scope string and forces an interactive prompt.

### Prompt Behaviour

The admin re-authentication uses `prompt: "login consent"` to ensure users always see the consent screen for the elevated scope. This avoids scenarios where Auth0 silently denies the scope because no prior consent exists.

## SPA Implementation Notes

Key behaviours within `web/src/routes/Admin.tsx`:

- **Role detection**: Uses the custom ID token claim `https://trigpointing.uk/roles` to determine whether to show the Admin link and gate the page.
- **Scope validation**: Decodes the access token and reads both the `scope` string and `permissions` array to determine whether `api:admin` is present.
- **Interactive errors**: Treats Auth0 errors such as `missing_scope`, `missing_required_scope`, `missing_refresh_token`, `consent_required`, and `login_required` as reasons to rerun the step-up flow.
- **Redirect handling**: Persists `returnTo` in `sessionStorage` and uses `Auth0CallbackHandler` to send the user back to `/admin` after Auth0 completes the redirect.
- **User feedback**: Displays “Admin access requires re-authentication. Redirecting to login in 5 seconds…” before initiating the re-login, giving users time to read console output when debugging.
- **Debug logging**: When `import.meta.env.DEV` is true, the component logs messages prefixed with `[admin-scope]`, showing token contents, error details, and redirect state.
- **Testing**: Vitest exercises permission-only tokens, consent errors, and invalid grant responses to prevent regressions (`web/src/routes/__tests__/Admin.test.tsx`).

## Auth0 Configuration Checklist

Ensure the SPA client for each environment (staging and production):

1. **Allowed API scopes** include `api:admin`, `api:write`, `api:read-pii`, and `offline_access`.
2. **Rotating Refresh Tokens** are enabled (Auth0 Dashboard → Applications → Settings → Advanced).
3. **Allow Offline Access** is checked (required for `offline_access` scope).
4. The **API (Audience)** corresponding to `https://api.trigpointing.me/` (staging) and `https://api.trigpointing.uk/` (production) trusts the SPA client to request the scopes above.
5. Callback, logout, and allowed web origins include the SPA URLs (`http://localhost:5173`, staging `/app`, production `/app`).

## Troubleshooting Guide

| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| Infinite redirects between `/admin` and Auth0 login | Refresh token missing | Confirm `offline_access` is requested by the SPA and allowed in Auth0. |
| No consent screen appears; `api:admin` never granted | Prompt missing or prior consent revoked | Verify `prompt: "login consent"` is present and Auth0 allows the scope (no tenant-level restriction). |
| Console shows `[admin-scope] Checked admin scope token` with `permissions: ["api:admin"]` but no `api:admin` in `scopes` | Token has permission but missing scope string | Auth0 should still deliver the scope string after step-up. Trigger re-authentication (consent screen) or inspect Auth0 logs to confirm policy. |
| `missing_required_scope` or `invalid_scope` errors | SPA client not allowed to request `api:admin` | Update the Auth0 API settings to permit the scope for the SPA client. |
| `login_required` / `consent_required` loop | User cancelled consent or browser blocked third-party cookies | Retry the step-up, ensure cookies enabled, consider using a private window. |

## Step-by-Step Manual Test

1. Sign in without admin scope (regular login).
2. Confirm `/admin` shows the spinner and logs the step-up attempt in the console.
3. Auth0 prompts for login/consent; approve the request.
4. After redirect, verify console log `[admin-scope] Admin scope present; displaying admin dashboard.` and that the page shows the admin dashboard.
5. Inspect the returned access token in the Network tab (`oauth/token`) to confirm `api:admin` and `offline_access` scopes.

## Regression Safety Nets

- Vitest suite covering admin scope flows: `npm run test:run -- routes/__tests__/Admin.test.tsx`.
- Console debug logs remain in production but only emit when `import.meta.env.DEV` is true (i.e., local development).
- Documentation kept in this file plus SCOPES references in API docs (`docs/auth/AUTH0_AUDIENCE_CONFIGURATION.md`) to maintain consistency.

Keeping this checklist in mind should prevent a repeat of the step-up issues encountered during implementation.

