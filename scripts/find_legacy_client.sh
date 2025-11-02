#!/bin/bash
# Find the legacy client in Auth0

# Use terraform to output tenant domain
TENANT_DOMAIN=$(terraform output -raw auth0_tenant_domain 2>/dev/null)
CLIENT_ID=$(terraform output -raw auth0_terraform_client_id 2>/dev/null)
CLIENT_SECRET=$(terraform output -raw auth0_terraform_client_secret 2>/dev/null)

if [ -z "$TENANT_DOMAIN" ]; then
  echo "Could not get tenant domain from terraform outputs"
  exit 1
fi

echo "Searching for 'legacy' client in Auth0 tenant: $TENANT_DOMAIN"
echo ""

# Get Management API token
TOKEN=$(curl -s --request POST \
  --url "https://$TENANT_DOMAIN/oauth/token" \
  --header 'content-type: application/json' \
  --data "{
    \"client_id\":\"$CLIENT_ID\",
    \"client_secret\":\"$CLIENT_SECRET\",
    \"audience\":\"https://$TENANT_DOMAIN/api/v2/\",
    \"grant_type\":\"client_credentials\"
  }" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "Failed to get Management API token"
  exit 1
fi

# List all clients and filter for "legacy"
curl -s --request GET \
  --url "https://$TENANT_DOMAIN/api/v2/clients?fields=client_id,name,app_type&include_fields=true" \
  --header "authorization: Bearer $TOKEN" | \
  jq -r '.[] | select(.name | test("legacy"; "i")) | "Name: \(.name)\nClient ID: \(.client_id)\nApp Type: \(.app_type)\n"'

