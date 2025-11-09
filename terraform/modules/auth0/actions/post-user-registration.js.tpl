/**
 * Auth0 Post User Registration Action for ${environment}
 * 
 * This Action is triggered after a user successfully registers via Auth0.
 * It provisions the user in the FastAPI/MySQL database via webhook.
 * 
 * Flow:
 * 1. Generate nickname from email prefix
 * 2. Try to create user via POST /v1/users (authenticated with shared secret)
 * 3. On username collision (409), retry with random 6-digit suffix
 * 4. Up to 10 retries with different random suffixes
 * 5. Set final nickname in Auth0 user metadata
 * 
 * Environment Variables (from Secrets):
 * - FASTAPI_URL: Base URL of FastAPI (e.g., https://api.trigpointing.uk)
 * - WEBHOOK_SHARED_SECRET: Shared secret for webhook authentication
 * - AUTH0_DOMAIN: Auth0 tenant domain (e.g., trigpointing.eu.auth0.com)
 * - M2M_CLIENT_ID: Auth0 M2M client ID (for Management API only)
 * - M2M_CLIENT_SECRET: Auth0 M2M client secret (for Management API only)
 */

exports.onExecutePostUserRegistration = async (event, api) => {
  const axios = require('axios');
  
  // Verify we have the webhook shared secret
  if (!event.secrets.WEBHOOK_SHARED_SECRET) {
    console.error('[${environment}] WEBHOOK_SHARED_SECRET not configured - cannot provision user');
    return;
  }
  
  // Step 1: Generate base nickname from email prefix
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
      // Authenticate with shared secret
      await axios.post(
        event.secrets.FASTAPI_URL + '/v1/users',
        payload,
        {
          headers: {
            'X-Webhook-Secret': event.secrets.WEBHOOK_SHARED_SECRET,
            'X-Auth0-Webhook': 'post-user-registration',
            'Content-Type': 'application/json'
          },
          timeout: 5000
        }
      );
      
      console.log('[${environment}] User provisioned successfully:', event.user.user_id, 'with nickname:', nickname);
      
      // Step 6: Update Auth0 user profile with nickname and name
      // This requires Management API access - get M2M token (not cached to avoid quota issues with retries)
      try {
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
        
        await api.user.setAppMetadata('final_nickname', nickname);
        
        await axios.patch(
          `https://$${event.secrets.AUTH0_DOMAIN}/api/v2/users/$${encodeURIComponent(event.user.user_id)}`,
          {
            nickname: nickname,
            name: nickname  // Set name to match nickname for consistency
          },
          {
            headers: {
              'Authorization': `Bearer $${mgmtTokenResponse.data.access_token}`,
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

