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
 * 5. Store final nickname in app_metadata (no M2M token required)
 * 
 * Environment Variables (from Secrets):
 * - FASTAPI_URL: Base URL of FastAPI (e.g., https://api.trigpointing.uk)
 * - WEBHOOK_SHARED_SECRET: Shared secret for webhook authentication
 * 
 * Note: Database is the source of truth for usernames. Auth0 nickname/name fields
 * may differ from database username due to collision retries, but this is harmless.
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
            'Content-Type': 'application/json'
          },
          timeout: 5000
        }
      );
      
      console.log('[${environment}] User provisioned successfully:', event.user.user_id, 'with nickname:', nickname);
      
      // Step 6: Store final nickname in app_metadata for reference
      // Note: We don't update Auth0's nickname/name fields to avoid M2M quota usage
      // The database is the source of truth for usernames
      try {
        await api.user.setAppMetadata('final_nickname', nickname);
        await api.user.setAppMetadata('database_synced', new Date().toISOString());
        console.log('[${environment}] Stored final nickname in app_metadata:', nickname);
      } catch (error) {
        console.error('[${environment}] Failed to set app_metadata:', error.message);
        // Don't fail registration - not critical
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

