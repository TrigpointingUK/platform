import { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";

// Helper function to decode JWT payload
interface JWTPayload {
  scope?: string;
  permissions?: string[];
  [key: string]: unknown;
}

function decodeJWT(token: string): JWTPayload | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload) as JWTPayload;
  } catch (error) {
    console.error("Failed to decode JWT:", error);
    return null;
  }
}

export default function Admin() {
  const { user, getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const [hasAdminScope, setHasAdminScope] = useState<boolean | null>(null);
  const [isCheckingScope, setIsCheckingScope] = useState(true);

  // Check if user has api-admin role (from ID token)
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  // Check for api:admin scope in access token
  useEffect(() => {
    const checkAdminScope = async () => {
      setIsCheckingScope(true);

      try {
        const token = await getAccessTokenSilently({ cacheMode: "on" });
        const decoded = decodeJWT(token);

        if (decoded) {
          // Extract scopes
          let scopes: string[] = [];

          if (decoded.scope && typeof decoded.scope === "string") {
            scopes = decoded.scope.split(" ").filter((s: string) => s);
          } else if (
            decoded.permissions &&
            Array.isArray(decoded.permissions)
          ) {
            scopes = decoded.permissions;
          }

          const hasScope = scopes.includes("api:admin");
          setHasAdminScope(hasScope);

          // If user has admin role but not admin scope, trigger re-authentication
          if (hasAdminRole && !hasScope) {
            // Wait a moment before redirecting so user can see what's happening
            setTimeout(() => {
              loginWithRedirect({
                authorizationParams: {
                  scope: "openid profile email api:write api:read-pii api:admin",
                  prompt: "login", // Force re-authentication for security
                },
                appState: { returnTo: "/admin" },
              });
            }, 2000);
          }
        } else {
          setHasAdminScope(false);
        }
      } catch (error) {
        console.error("Failed to check admin scope:", error);
        setHasAdminScope(false);
      } finally {
        setIsCheckingScope(false);
      }
    };

    checkAdminScope();
  }, [hasAdminRole, getAccessTokenSilently, loginWithRedirect]);

  // User doesn't have admin role at all
  if (!hasAdminRole) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <h1 className="text-2xl font-bold text-gray-800 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600">
                You do not have permission to access the admin area.
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  // Checking scope
  if (isCheckingScope || hasAdminScope === null) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <Spinner size="lg" />
              <p className="text-gray-600 mt-4">
                Verifying admin permissions...
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  // Has role but not scope - showing message before redirect
  if (!hasAdminScope) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <Spinner size="lg" />
              <p className="text-gray-600 mt-4">
                Admin access requires re-authentication.
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Redirecting to login...
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  // Has both role and scope - show admin page
  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        <Card className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-4">
            Admin Dashboard
          </h1>
          <p className="text-gray-600">
            Welcome to the admin area. More features coming soon.
          </p>
        </Card>

        {/* Placeholder sections for future admin features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              User Management
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              Content Moderation
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              System Settings
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              Analytics
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

