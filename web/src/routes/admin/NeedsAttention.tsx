import { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link } from "react-router-dom";
import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import Button from "../../components/ui/Button";
import {
  fetchNeedsAttentionTrigs,
  TrigNeedsAttentionListItem,
} from "../../lib/api";

const ADMIN_AUTH_PARAMS = {
  audience: import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined,
  scope: "openid profile email api:write api:read-pii offline_access api:admin",
};

export default function NeedsAttention() {
  const { getAccessTokenSilently, user } = useAuth0();
  const [trigs, setTrigs] = useState<TrigNeedsAttentionListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const limit = 20;

  // Check if user has admin role
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  useEffect(() => {
    if (!hasAdminRole) {
      return;
    }

    let cancelled = false;

    const fetchTrigs = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });
        const data = await fetchNeedsAttentionTrigs({ skip, limit }, token);

        if (!cancelled) {
          setTrigs(data.items);
          setTotal(data.pagination.total);
          setHasMore(data.pagination.has_more);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load trigpoints");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchTrigs();

    return () => {
      cancelled = true;
    };
  }, [getAccessTokenSilently, hasAdminRole, skip]);

  if (!hasAdminRole) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <h1 className="text-2xl font-bold text-gray-800 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600">
                You do not have permission to access this page.
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  const handlePrevious = () => {
    setSkip(Math.max(0, skip - limit));
  };

  const handleNext = () => {
    setSkip(skip + limit);
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        <Card className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">
                Trigpoints Needing Attention
              </h1>
              <p className="text-gray-600">
                Manage trigpoints flagged for admin review
              </p>
            </div>
            <Link
              to="/admin"
              className="text-[#046935] hover:text-[#035228] font-medium"
            >
              ← Back to Admin
            </Link>
          </div>
        </Card>

        {isLoading && (
          <Card>
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="ml-3 text-gray-600">Loading trigpoints...</span>
            </div>
          </Card>
        )}

        {error && (
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600">Error: {error}</p>
            </div>
          </Card>
        )}

        {!isLoading && !error && trigs.length === 0 && (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-600">
                No trigpoints currently need attention.
              </p>
            </div>
          </Card>
        )}

        {!isLoading && !error && trigs.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-4 mb-6">
              {trigs.map((trig) => (
                <Card key={trig.id} className="hover:shadow-lg transition-shadow">
                  <Link
                    to={`/admin/trigs/${trig.id}/edit`}
                    className="block"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h2 className="text-xl font-semibold text-gray-800 mb-1">
                          {trig.name}
                        </h2>
                        <p className="text-sm text-gray-600">
                          Waypoint: {trig.waypoint} | Condition: {trig.condition} | 
                          Flag value: {trig.needs_attention}
                        </p>
                      </div>
                      {trig.upd_timestamp && (
                        <div className="text-sm text-gray-500 ml-4">
                          Last updated:{" "}
                          {new Date(trig.upd_timestamp).toLocaleDateString()}
                        </div>
                      )}
                    </div>

                    {trig.attention_comment && (
                      <div className="bg-gray-50 p-3 rounded-md">
                        <div className="text-xs text-gray-600 mb-1 font-medium">
                          Comment History:
                        </div>
                        <div className="text-sm text-gray-700 whitespace-pre-line line-clamp-3">
                          {trig.attention_comment}
                        </div>
                      </div>
                    )}

                    <div className="mt-3 text-[#046935] hover:text-[#035228] text-sm font-medium">
                      Edit trigpoint →
                    </div>
                  </Link>
                </Card>
              ))}
            </div>

            <Card>
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Showing {skip + 1} - {Math.min(skip + limit, total)} of {total}{" "}
                  trigpoints
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handlePrevious}
                    disabled={skip === 0}
                    variant="secondary"
                  >
                    ← Previous
                  </Button>
                  <Button
                    onClick={handleNext}
                    disabled={!hasMore}
                    variant="secondary"
                  >
                    Next →
                  </Button>
                </div>
              </div>
            </Card>
          </>
        )}
      </div>
    </Layout>
  );
}

