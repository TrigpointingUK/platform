# Admin Authentication Flow

## Overview

This document explains how admin authentication works in the TrigpointingUK application, specifically the flow for users with the `api-admin` role to access admin-only features.

## The Challenge

When Auth0 RBAC (Role-Based Access Control) is enabled with `enforce_policies = true`, Auth0 will only grant permissions/scopes that meet **both** of these conditions:

1. The permission is assigned to the user through their roles
2. The permission is explicitly requested in the `scope` parameter during authentication

This means that even if a user has the `api-admin` role with the `api:admin` permission, they won't receive the `api:admin` scope in their access token unless it was explicitly requested during login.

## The Solution

We've implemented a two-step authentication flow:

### Step 1: Initial Login
Users log in normally through the main application. The initial authentication requests these scopes:
- `openid`
- `profile` 
- `email`
- `api:write`
- `api:read-pii`

Note that `api:admin` is NOT requested initially for security reasons - we want admin access to require explicit re-authentication.

### Step 2: Admin Access
When a user with the `api-admin` role visits the `/admin` page:

1. The `useAdminAuth` hook checks if the current access token contains the `api:admin` scope
2. If not, it redirects the user back to Auth0 with:
   - All previous scopes PLUS `api:admin`
   - `prompt: "login"` to force re-authentication
   - A query parameter to prevent redirect loops

3. After successful re-authentication, the user receives a new access token that includes the `api:admin` scope
4. The admin page is then displayed

## Implementation Details

### Frontend Components

1. **`useAdminAuth` Hook** (`/web/src/hooks/useAdminAuth.ts`)
   - Checks if user has `api-admin` role (from ID token)
   - Checks if current access token has `api:admin` scope
   - Handles the re-authentication flow if needed
   - Prevents redirect loops using URL parameters

2. **Admin Route** (`/web/src/routes/Admin.tsx`)
   - Uses the `useAdminAuth` hook
   - Shows appropriate UI states:
     - Access denied (no admin role)
     - Loading/verifying permissions
     - Redirecting for authentication
     - Admin dashboard (successful auth)

### Auth0 Configuration

1. **API Resource Server**
   - RBAC enabled with `enforce_policies = true`
   - Defines `api:admin` scope

2. **Roles**
   - `api-admin` role has permissions for `api:admin`, `api:write`, and `api:read-pii`

3. **Post-Login Action**
   - Adds user roles to both ID and access tokens as custom claims
   - Does NOT automatically add role permissions to tokens (this is intentional)

### Backend API

The FastAPI backend uses the `require_admin()` dependency to check for the `api:admin` scope in the access token for admin endpoints.

## Security Benefits

This approach provides several security benefits:

1. **Explicit Admin Authentication**: Admin access requires a fresh authentication, even if the user is already logged in
2. **Scope Minimization**: Regular users don't receive admin scopes they don't need
3. **Audit Trail**: Each admin access attempt requires re-authentication, creating an audit trail
4. **No Accidental Admin Access**: Admin permissions are only granted when explicitly requested

## Troubleshooting

### Common Issues

1. **Redirect Loop**: If the admin page keeps redirecting, check:
   - The `admin_auth_attempted` query parameter is being properly set/cleared
   - The Auth0 application has the correct callback URLs configured
   - The audience parameter matches your API identifier

2. **Missing Scope**: If the `api:admin` scope is not in the token after re-auth:
   - Verify the user has the `api-admin` role in Auth0
   - Check that the role has the `api:admin` permission assigned
   - Ensure RBAC is enabled on the API resource server

3. **Access Denied**: If a user with admin role can't access admin features:
   - Clear browser cache and cookies
   - Log out completely and log back in
   - Check the browser console for specific error messages

## Future Improvements

1. Consider implementing a "sudo mode" where admin actions require re-authentication within a session
2. Add more granular admin permissions (e.g., `api:admin:read`, `api:admin:write`)
3. Implement admin session timeouts for additional security
