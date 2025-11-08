/**
 * Auth0 Post User Registration Action for ${environment}
 * 
 * This Action is triggered after a user successfully registers via Auth0.
 * It provisions the user in the FastAPI/MySQL database via webhook.
 * 
 * Flow:
 * 1. Obtain M2M token using client credentials (OAuth2 client_credentials flow)
 *    - Caches tokens for 50 minutes to avoid quota exhaustion
 * 2. Generate nickname from email prefix
 * 3. Try to create user via POST /v1/users
 * 4. On username collision (409), retry with random 6-digit suffix
 * 5. Up to 10 retries with different random suffixes
 * 6. Set final nickname in Auth0 user metadata (using cached Management API token)
 * 
 * Environment Variables (from Secrets):
 * - FASTAPI_URL: Base URL of FastAPI (e.g., https://api.trigpointing.me)
 * - M2M_CLIENT_ID: Auth0 M2M client ID
 * - M2M_CLIENT_SECRET: Auth0 M2M client secret
 * - AUTH0_DOMAIN: Auth0 tenant domain (e.g., trigpointing-me.eu.auth0.com)
 * - API_AUDIENCE: FastAPI API audience (e.g., https://api.trigpointing.me/)
 * - WEBHOOK_SHARED_SECRET: Shared secret for fallback authentication (optional)
 */

exports.onExecutePostUserRegistration = async (event, api) => {
  const axios = require('axios');
  
  // Step 1: Obtain M2M token using client credentials (with caching)
  let m2mToken;
  const apiTokenCacheKey = 'fastapi_m2m_token';
  
  // Try to get cached token first
  const cachedApiToken = api.cache.get(apiTokenCacheKey);
  if (cachedApiToken && cachedApiToken.value) {
    m2mToken = cachedApiToken.value;
    console.log('[${environment}] Using cached M2M token for FastAPI');
  } else {
    try {
      const tokenResponse = await axios.post(
        `https://$${event.secrets.AUTH0_DOMAIN}/oauth/token`,
        {
          grant_type: 'client_credentials',
          client_id: event.secrets.M2M_CLIENT_ID,
          client_secret: event.secrets.M2M_CLIENT_SECRET,
          audience: event.secrets.API_AUDIENCE
        },
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: 5000
        }
      );
      m2mToken = tokenResponse.data.access_token;
      
      // Cache token for 50 minutes (tokens typically last 1 hour, cache for safety margin)
      api.cache.set(apiTokenCacheKey, m2mToken, { ttl: 3000000 }); // 50 minutes in ms
      console.log('[${environment}] Cached new M2M token for FastAPI');
    } catch (error) {
      console.error('[${environment}] Failed to obtain M2M token:', error.response?.data || error.message);
      console.error('[${environment}] M2M token request failed - will use shared secret fallback');
      m2mToken = null; // Will trigger shared secret fallback
    }
  }
  
  // Step 2: Generate base nickname from email prefix
  // Auth0 signup only collects email/password by default
  // Nickname allows spaces and special characters (unlike username)
  const baseNickname = event.user.nickname || event.user.email.split('@')[0];
  
  // Step 3-5: Try to create user, handling username collisions with random suffixes
  let nickname = baseNickname;
  let attempt = 0;
  const maxAttempts = 10;
  
  while (attempt < maxAttempts) {
    const payload = {
      username: nickname,  // Maps to user.name (nickname/display name)
      email: event.user.email,
      auth0_user_id: event.user.user_id
    };
    
    try {
      // Build headers with either M2M token or shared secret fallback
      const headers = {
        'Content-Type': 'application/json'
      };
      
      if (m2mToken) {
        headers['Authorization'] = `Bearer $${m2mToken}`;
      } else if (event.secrets.WEBHOOK_SHARED_SECRET) {
        headers['X-Webhook-Secret'] = event.secrets.WEBHOOK_SHARED_SECRET;
        console.log('[${environment}] Using shared secret fallback for webhook authentication');
      } else {
        console.error('[${environment}] No M2M token and no shared secret available');
        return; // Cannot authenticate
      }
      
      await axios.post(
        event.secrets.FASTAPI_URL + '/v1/users',
        payload,
        {
          headers: headers,
          timeout: 5000
        }
      );
      
      console.log('[${environment}] User provisioned successfully:', event.user.user_id, 'with nickname:', nickname);
      
      // Step 6: Update Auth0 user profile with nickname and name
      // Use Management API to set both nickname and name fields (with cached token)
      try {
        let mgmtToken;
        const mgmtTokenCacheKey = 'mgmt_api_m2m_token';
        
        // Try cached Management API token first
        const cachedMgmtToken = api.cache.get(mgmtTokenCacheKey);
        if (cachedMgmtToken && cachedMgmtToken.value) {
          mgmtToken = cachedMgmtToken.value;
          console.log('[${environment}] Using cached Management API token');
        } else {
          const mgmtTokenResponse = await axios.post(
            `https://$${event.secrets.AUTH0_DOMAIN}/oauth/token`,
            {
              grant_type: 'client_credentials',
              client_id: event.secrets.M2M_CLIENT_ID,
              client_secret: event.secrets.M2M_CLIENT_SECRET,
              audience: `https://$${event.secrets.AUTH0_DOMAIN}/api/v2/`
            },
            { headers: { 'Content-Type': 'application/json' }, timeout: 5000 }
          );
          mgmtToken = mgmtTokenResponse.data.access_token;
          
          // Cache Management API token for 50 minutes
          api.cache.set(mgmtTokenCacheKey, mgmtToken, { ttl: 3000000 });
          console.log('[${environment}] Cached new Management API token');
        }
        
        await axios.patch(
          `https://$${event.secrets.AUTH0_DOMAIN}/api/v2/users/$${encodeURIComponent(event.user.user_id)}`,
          {
            nickname: nickname,
            name: nickname  // Set name to match nickname for consistency
          },
          {
            headers: {
              'Authorization': `Bearer $${mgmtToken}`,
              'Content-Type': 'application/json'
            },
            timeout: 5000
          }
        );
        console.log('[${environment}] Updated Auth0 profile with nickname and name:', nickname);
      } catch (error) {
        console.error('[${environment}] Failed to update Auth0 profile:', error.response?.data || error.message);
        // Don't fail registration - user can update later
      }
      
      return; // Success!
      
    } catch (error) {
      if (error.response?.status === 409 && 
          error.response?.data?.detail?.toLowerCase().includes('username')) {
        // Username collision - generate random 6-digit suffix
        // This avoids predictable patterns and potential DoS attacks
        const randomSuffix = Math.floor(100000 + Math.random() * 900000);
        nickname = `$${baseNickname}$${randomSuffix}`;
        attempt++;
        console.log(`[${environment}] Username collision on attempt $${attempt}, trying: $${nickname}`);
      } else {
        // Other error - log but don't fail registration
        console.error('[${environment}] User provisioning failed:', error.response?.data || error.message);
        console.error('[${environment}] User registered in Auth0 but not in database. Manual sync may be required.');
        return;
      }
    }
  }
  
  console.error('[${environment}] Failed to find unique username after', maxAttempts, 'attempts for user:', event.user.user_id);
  console.error('[${environment}] User registered in Auth0 but not in database. Manual provisioning required.');
};

