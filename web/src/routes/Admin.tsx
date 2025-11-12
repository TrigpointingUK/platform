import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import { useAdminAuth } from "../hooks/useAdminAuth";

export default function Admin() {
  const { hasAdminRole, hasAdminScope, isLoading } = useAdminAuth();

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

  // Loading or checking permissions
  if (isLoading || hasAdminScope === null) {
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

