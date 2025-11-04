import { useParams, Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import LogCard from "../components/logs/LogCard";
import { useLogDetail } from "../hooks/useLogDetail";

export default function LogDetail() {
  const { logId } = useParams<{ logId: string }>();
  const logIdNum = logId ? parseInt(logId, 10) : null;

  const {
    data: log,
    isLoading,
    error,
  } = useLogDetail(logIdNum!);

  if (!logIdNum) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600">Invalid log ID</p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600">Failed to load log details</p>
            <Link
              to="/"
              className="text-trig-green-600 hover:underline mt-4 inline-block"
            >
              ← Back to Home
            </Link>
          </Card>
        </div>
      </Layout>
    );
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <Spinner size="lg" />
            <p className="text-center text-gray-600 mt-4">Loading log...</p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (!log) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600">Log not found</p>
            <Link
              to="/"
              className="text-trig-green-600 hover:underline mt-4 inline-block"
            >
              ← Back to Home
            </Link>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <div className="mb-4">
          <Link 
            to={`/trig/${log.trig_id}`} 
            className="text-trig-green-600 hover:underline"
          >
            ← Back to {log.trig_name || `Trigpoint TP${log.trig_id.toString().padStart(4, '0')}`}
          </Link>
        </div>

        {/* Single Log Card */}
        <LogCard log={log} />
      </div>
    </Layout>
  );
}

