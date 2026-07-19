# Third-Party API Integration Guide

This guide explains how third-party applications can integrate with the TrigpointingUK API using Auth0 for authentication and authorisation.

## Overview

Third-party applications can access the TrigpointingUK API on behalf of users through delegated authorisation. This allows external apps, mobile applications, or services to:

- Read public trigpoint data
- Create and update logs and photos on behalf of users
- Access trig statistics and geolocation services

**Important**: Third-party apps cannot access user PII (email addresses, real names) or modify user profiles directly. This protects user privacy whilst enabling a vibrant ecosystem.

## Integration Patterns

### 1. Mobile App Integration (Recommended)

For mobile apps that act on behalf of a user:

1. **Register your application** in Auth0 as a Native Application
2. **Request user authorisation** using OAuth2 Authorization Code flow with PKCE
3. **Use granted scopes** to access the API on the user's behalf

**Granted scopes**:
- `api:write` - Create/update logs, photos, trigs for the authorised user
- Public read access (implicit with authentication)

**NOT granted**:
- `api:read-pii` - Cannot access user email addresses or real names
- `api:admin` - Cannot modify other users' data

### 2. Server-to-Server Integration (M2M)

For trusted server applications requiring direct API access:

1. **Contact administrators** to discuss your use case
2. **M2M client credentials** may be provided for approved integrations
3. **Limited scopes** granted based on integration requirements

This pattern is less common and requires manual approval.

## Step-by-Step: Mobile App Integration

### 1. Register Your Application

Contact the TrigpointingUK administrators with:
- Application name and description
- Callback URLs (e.g., `com.yourapp://callback`)
- Logout URLs
- Website/app store links

You'll receive:
- Client ID
- Auth0 domain (e.g., `auth.trigpointing.uk`)

### 2. Implement OAuth2 Authorization Code Flow with PKCE

**Initiate authorisation**:
```
GET https://auth.trigpointing.uk/authorize?
  response_type=code&
  client_id=YOUR_CLIENT_ID&
  redirect_uri=com.yourapp://callback&
  audience=https://api.trigpointing.uk/&
  scope=openid profile offline_access&
  state=RANDOM_STATE&
  code_challenge=CODE_CHALLENGE&
  code_challenge_method=S256
```

**The `audience` parameter is required.** Without it, Auth0 issues an opaque
token for the userinfo endpoint instead of a JWT for the TrigpointingUK API,
and every API call will return 401. Use `https://api.trigpointing.uk/`
(production) or `https://api.trigpointing.me/` (staging) — including the
trailing slash.

Include `offline_access` to receive a refresh token. Refresh tokens are
**rotating**: every refresh returns a new refresh token and invalidates the
previous one, so always store the newest value.

On first authorisation, users see an Auth0 consent screen listing the access
your app requested. Users can revoke this consent at any time from the
Preferences page on trigpointing.uk, which invalidates your refresh tokens —
handle a failed refresh by restarting the login flow.

**Exchange code for token**:
```
POST https://auth.trigpointing.uk/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTHORIZATION_CODE&
redirect_uri=com.yourapp://callback&
client_id=YOUR_CLIENT_ID&
code_verifier=CODE_VERIFIER
```

**Response**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "v1...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "openid profile offline_access"
}
```

Note: API scopes such as `api:write` are not currently included in
third-party tokens — write access to your own logs and photos is authorised
by identity and ownership, so authenticated requests work without it. Request
only `openid profile offline_access` for now; this may change in a future
API version (announced via the changelog).

### 3. Use Access Token for API Calls

Include the access token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJ..." \
  https://api.trigpointing.uk/api/v1/trigs
```

### 4. Example: Create a Log Entry

```bash
POST https://api.trigpointing.uk/api/v1/logs
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "trig_id": 12345,
  "logged_date": "2025-10-23",
  "condition": "G",
  "comment": "Logged via MyAwesomeApp"
}
```

The log will be created under the authorised user's account.

## Scope Reference

| Scope | Description | Granted to 3rd Party |
|-------|-------------|---------------------|
| `api:write` | Create/update own logs, photos, trigs | ✅ Yes |
| `api:read-pii` | Access user PII (email, realName) | ❌ No |
| `api:admin` | Administrative access | ❌ No |

## API Endpoints Available to Third-Party Apps

### Public Endpoints (No Auth Required)
- `GET /api/v1/trigs` - List all trigpoints
- `GET /api/v1/trigs/{id}` - Get trigpoint details
- `GET /api/v1/users/{id}/badge` - Get user badge image

### Authenticated Endpoints (With `api:write` Scope)
- `POST /api/v1/logs` - Create log entry
- `PATCH /api/v1/logs/{id}` - Update own log entry
- `DELETE /api/v1/logs/{id}` - Delete own log entry
- `POST /api/v1/photos` - Upload photo
- `PATCH /api/v1/photos/{id}` - Update own photo
- `GET /api/v1/users/me` - Get own user profile (public fields only)

### Restricted Endpoints (NOT Available)
- `PATCH /api/v1/users/me` - Update user profile (requires `api:read-pii`)
- `POST /api/v1/users` - Create users (internal only)

## Best Practices

### 1. Respect User Privacy
- Never attempt to scrape or infer PII
- Only request scopes you actually need
- Display clear privacy policies to users

### 2. Handle Token Expiry
- Access tokens expire after 1 hour in production (2 minutes on staging —
  deliberately short so refresh handling gets exercised during development)
- Implement token refresh using refresh tokens (rotating: store the new
  refresh token returned by every refresh)
- Handle 401 responses gracefully; a failed refresh means consent was revoked
  or the token expired — restart the login flow

### 3. Rate Limiting
- Be respectful of API resources
- Implement exponential backoff for retries
- Cache responses where appropriate

### 4. Error Handling

Common error responses:

| Status | Meaning | Action |
|--------|---------|--------|
| 401 | Unauthorised | Token expired or invalid - re-authenticate |
| 403 | Forbidden | Missing required scope - request correct permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limited - back off |

### 5. Branding
- Clearly indicate your app is "powered by TrigpointingUK"
- Use official logos and branding (available on request)
- Link back to trigpointing.uk

## Security Considerations

### Do's ✅
- Use PKCE for mobile apps (prevents authorisation code interception)
- Store tokens securely (iOS Keychain, Android KeyStore)
- Use HTTPS for all API calls
- Validate token expiry before each request
- Log out users properly (clear tokens)

### Don'ts ❌
- Don't store tokens in plaintext
- Don't hardcode client secrets in mobile apps (use PKCE instead)
- Don't share access tokens between users
- Don't attempt to reverse-engineer or bypass scopes

## Support and Updates

### Getting Help
- Technical issues: Open an issue on GitHub
- Integration questions: Contact administrators via forum
- Security concerns: Email security@trigpointing.uk

### API Changes
- Breaking changes will be communicated 6 months in advance
- New endpoints and features announced via changelog
- Subscribe to API updates: https://api.trigpointing.uk/changelog

## Example Integrations

### Mobile App (React Native)
```javascript
import { authorize } from 'react-native-app-auth';

const config = {
  clientId: 'YOUR_CLIENT_ID',
  redirectUrl: 'com.yourapp://callback',
  scopes: ['openid', 'profile', 'offline_access'],
  additionalParameters: {
    audience: 'https://api.trigpointing.uk/', // required — see above
  },
  serviceConfiguration: {
    authorizationEndpoint: 'https://auth.trigpointing.uk/authorize',
    tokenEndpoint: 'https://auth.trigpointing.uk/oauth/token',
  },
};

const authState = await authorize(config);
// Use authState.accessToken for API calls
```

### Python Script
```python
import requests
from requests_oauthlib import OAuth2Session

client_id = 'YOUR_CLIENT_ID'
redirect_uri = 'http://localhost:8080/callback'
authorization_base_url = 'https://auth.trigpointing.uk/authorize'
token_url = 'https://auth.trigpointing.uk/oauth/token'

# Get authorisation URL
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=['api:write'])
authorization_url, state = oauth.authorization_url(authorization_base_url)
print(f'Visit: {authorization_url}')

# After user authorises, exchange code for token
callback_response = input('Paste callback URL: ')
token = oauth.fetch_token(token_url, authorization_response=callback_response)

# Use token for API calls
response = requests.get(
    'https://api.trigpointing.uk/api/v1/trigs',
    headers={'Authorization': f"Bearer {token['access_token']}"}
)
```

## Changelog

### 2026-07-19
- Documented the required `audience` parameter on `/authorize` (omitting it
  yields an opaque token the API rejects)
- Recommended scopes are now `openid profile offline_access`; API scopes are
  not currently issued to third-party apps (identity/ownership authorisation)
- Third-party apps are registered as non-first-party clients: users see an
  Auth0 consent screen and can revoke access from their Preferences page
- Documented rotating refresh tokens

### 2025-10-23
- Initial documentation for simplified scope model
- Introduced `api:write`, `api:read-pii`, `api:admin` scopes
- Deprecated granular resource-based scopes

## Frequently Asked Questions

**Q: Can I create user accounts via the API?**  
A: No, user registration is handled through Auth0 directly. Third-party apps can only act on behalf of existing users.

**Q: Why can't I access user email addresses?**  
A: To protect user privacy, the `api:read-pii` scope is reserved for first-party applications. Third-party apps can access public profile information (username, stats) but not contact details.

**Q: Can I build a competing mobile app?**  
A: Yes! The API is designed to encourage an open ecosystem. Build the best app you can - competition benefits users.

**Q: How do I get M2M client credentials?**  
A: Contact administrators with your use case. M2M access is granted on a case-by-case basis for legitimate integrations.

**Q: Will the API always be free?**  
A: The API is currently free for all users. If commercial rate limits are ever introduced, hobbyist/community projects will remain free.

