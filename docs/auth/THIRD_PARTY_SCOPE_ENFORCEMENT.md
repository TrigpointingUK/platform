# Third-Party Scope Enforcement — Future Work

**Status: deferred (July 2026).** Tenant support for third-party applications is
in place (domain-level connection, non-first-party clients, enforced consent
screen, Connected Applications panel in the SPA). What is NOT yet in place is
scope-based enforcement: today the API authorises ordinary writes by identity +
ownership, and `api:write` / `api:read-pii` are decorative. This document
records the agreed design for closing that gap so it isn't re-derived later.

## Background (why this is needed)

- The API resource server has RBAC enabled (`enforce_policies = true`,
  `token_dialect = access_token_authz`). Requested API scopes are intersected
  with the user's role permissions when the token is minted.
- Only the `api-admin` role holds any API permissions, so ordinary users'
  tokens never contain `api:write` or `api:read-pii` — even if requested and
  consented to.
- The API only enforces `api:admin` (see `require_admin` /
  `require_owner_or_admin` in `api/api/deps.py`). Write endpoints rely on
  `get_current_user` + ownership checks.
- Consequence: the consent screen can show a scope the token will never
  contain, and the published promise that third-party apps cannot access PII
  is not enforced per-client — a third-party user token is indistinguishable
  from a first-party one except by its `azp` claim.

## Design: layered scope model via the post-login Action

All changes below go in the Terraform-managed post-login Action
(`terraform/modules/auth0/actions/post-login.js.tpl`), applied to **both**
tenants. Post-login Actions also run on refresh-token exchanges, so policy
changes take effect within one access-token lifetime.

### Layer 1 — baseline + tenant policy (no per-user state)

For tokens whose audience is the TUK API:

1. `api.accessToken.addScope("api:write")` for every authenticated user.
   Rationale: a grant held by 100% of users is a constant, not role state —
   no `api-user` role, no Management API backfill, no per-user failure mode.
2. If `event.client` is **not first-party** (maintain an explicit first-party
   client-ID list injected via the Terraform template, or read
   `event.client.metadata`): `api.accessToken.removeScope("api:read-pii")`
   unconditionally. This enforces the privacy promise in
   `THIRD_PARTY_INTEGRATION.md`.

### Layer 2 — per-user opt-in for PII (adds user choice)

Store per-user-per-client grants in Auth0 `app_metadata`:

```json
{ "third_party_grants": { "<client_id>": ["api:write", "api:read-pii"] } }
```

- Action: for third-party clients, intersect requested API scopes with the
  stored list (default: `api:write` only). `event.user.app_metadata` is
  available in the Action without extra API calls.
- SPA: extend the Connected Applications panel with per-app permission
  toggles; writes go through a new API endpoint to the Management API
  (`update:users` scope — already granted to the M2M client).
- Revocation property: user unticks PII → next refresh-token exchange strips
  the scope. No grant deletion needed.

### Layer 3 — custom consent screen (optional, deluxe)

Auth0's consent prompt is binary (accept all / decline). For genuine per-scope
checkboxes at authorisation time, use `api.redirect.sendUserTo()` from the
Action to a TUK-hosted consent page on first third-party login, store choices,
resume login, and strip scopes accordingly. Meaningful work (signed redirect
payload, resume endpoint, session handling) — only worth it if the third-party
ecosystem grows. Not required for Layers 1–2.

## API-side enforcement (fail closed)

Once Layer 1 ships and tokens are trustworthy:

1. Add `require_scopes("api:write")` to log/photo/trig write endpoints
   (`api/api/v1/endpoints/logs.py`, `photos.py`, …). Ownership checks remain —
   scopes gate *what kind* of action, ownership gates *whose data*.
2. Add `require_scopes("api:read-pii")` to endpoints returning or mutating
   email/PII (e.g. the PII fields of `GET/PATCH /v1/users/me`) — either
   reject, or filter PII fields from the response when the scope is absent.
3. Only then update the SPA if needed (it already requests
   `api:write api:read-pii offline_access`; see
   `docs/auth/admin-scope-step-up.md`).

**Ordering matters:** ship the Action first, verify tokens carry the scopes in
both environments (staging's 2-minute token lifetime makes refresh behaviour
easy to observe), then turn on API enforcement. Doing it in the other order
locks out every user of every app simultaneously.

## Gotchas recorded during design

- Consent happens **before** RBAC filtering: users can consent to a scope the
  token won't contain. Until Layer 1 ships, third-party apps should request
  only `openid profile offline_access`.
- Classic `auth0_client_grant` resources (subject_type `client`, the default)
  only apply to `client_credentials`. However, **third-party clients require a
  client grant with `subject_type = "user"`** before they may request tokens
  for a resource server at all — without one, `/authorize` fails with
  "Client is not authorized to access resource server". The scopes on that
  grant are a per-client ceiling for user flows, so
  `auth0_client_grant.third_party_to_api` in the module (which grants only
  `api:write`) already enforces "no `api:read-pii` / `api:admin` for third
  parties" at the Auth0 layer. Layer 1's `removeScope("api:read-pii")` remains
  useful as belt-and-braces and for any first-party-but-untrusted cases, but
  it is no longer the only enforcement point.
- The domain-level connection is usable by every third-party client in the
  tenant. OIDC Dynamic Application Registration must stay **disabled** (see
  comment on `auth0_connection.database` in the module).
- `extract_scopes()` in `api/core/security.py` merges the `scope` string and
  the RBAC `permissions` array; Action-added scopes appear in `scope` only —
  which it already handles.
