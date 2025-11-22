import { Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import Sidebar from "../components/layout/Sidebar";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import LogList from "../components/logs/LogList";
import { useSiteStats } from "../hooks/useSiteStats";
import { useRecentLogs } from "../hooks/useRecentLogs";
import { useNews } from "../hooks/useNews";

function WelcomeSection() {
  return (
    <Card className="mb-6">
      <h1 className="text-4xl font-bold text-trig-green-600 mb-4">
        Welcome to Trigpointing UK
      </h1>
      <p className="text-lg text-gray-700 mb-4">
        The UK's premier resource for triangulation pillars and survey markers.
        Join thousands of enthusiasts exploring Britain's geodetic heritage.
      </p>
      <div className="flex gap-3 flex-wrap w-full">
        <Button variant="primary" className="flex-1 min-w-[140px]">
          <Link
            to="/find-trigs"
            className="block w-full text-center text-current"
          >
            Nearest
          </Link>
        </Button>
        <Button variant="primary" className="flex-1 min-w-[140px]">
          <Link to="/map" className="block w-full text-center text-current">
            Map
          </Link>
        </Button>
      </div>
    </Card>
  );
}

function SiteStatsSection() {
  const { data: stats, isLoading, error } = useSiteStats();

  if (error) {
    return (
      <Card className="mb-6">
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-gray-800 inline">Site Statistics</h2>
          <span className="text-sm font-normal text-gray-600 ml-2">(Click to browse)</span>
        </div>
        <p className="text-red-600">Failed to load statistics</p>
      </Card>
    );
  }

  if (isLoading || !stats) {
    return (
      <Card className="mb-6">
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-gray-800 inline">Site Statistics</h2>
          <span className="text-sm font-normal text-gray-600 ml-2">(Click to browse)</span>
        </div>
        <Spinner size="md" />
      </Card>
    );
  }

  const statItems = [
    {
      label: "Trig Points",
      value: stats.total_trigs.toLocaleString(),
      icon: "/TUK-Logo.svg",
      color: "text-trig-green-600",
      link: "/trigs",
      isImage: true,
    },
    {
      label: "Registered Users",
      value: stats.total_users.toLocaleString(),
      icon: "/icons/links.png",
      color: "text-blue-600",
      link: "/users",
      isImage: true,
    },
    {
      label: "Visit Logs",
      value: stats.total_logs.toLocaleString(),
      icon: "/icons/stats.png",
      color: "text-purple-600",
      link: "/logs",
      isImage: true,
    },
    {
      label: "Photos",
      value: stats.total_photos.toLocaleString(),
      icon: "/icons/images.png",
      color: "text-orange-600",
      link: "/photos",
      isImage: true,
    },
  ];

  return (
    <Card className="mb-6">
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-gray-800 inline">Site Statistics</h2>
        <span className="text-sm font-normal text-gray-600 ml-2">(Click to browse)</span>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statItems.map((item) => (
          <Link
            key={item.label}
            to={item.link}
            className="text-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors block"
          >
            <div className="text-3xl mb-2 flex justify-center items-center h-12">
              {item.isImage ? (
                <img 
                  src={item.icon} 
                  alt={item.label} 
                  className="h-12 w-12 object-contain"
                />
              ) : (
                <span>{item.icon}</span>
              )}
            </div>
            <div className={`text-3xl font-bold ${item.color} mb-1`}>
              {item.value}
            </div>
            <div className="text-sm text-gray-600">{item.label}</div>
          </Link>
        ))}
      </div>
      {stats.recent_logs_7d > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-600 text-center">
          <strong>{stats.recent_logs_7d.toLocaleString()}</strong> logs added in
          the last 7 days •{" "}
          <strong>{stats.recent_users_30d.toLocaleString()}</strong> new users in
          the last 30 days
        </div>
      )}
    </Card>
  );
}

function NewsSection() {
  const { data: news, isLoading, error } = useNews();

  if (error) {
    return null; // Silently fail for news
  }

  if (isLoading) {
    return (
      <Card className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">Recent Site News</h2>
        <Spinner size="sm" />
      </Card>
    );
  }

  if (!news || news.length === 0) {
    return null;
  }

  return (
    <Card className="mb-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Recent Site News</h2>
      <div className="space-y-4">
        {news.slice(0, 3).map((item) => (
          <div key={item.id} className="border-l-4 border-trig-green-600 pl-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800">{item.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{item.summary}</p>
              </div>
              <time className="text-xs text-gray-500 whitespace-nowrap">
                {new Date(item.date).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
              </time>
            </div>
            {item.link && (
              <a
                href={item.link}
                className="text-sm text-trig-green-600 hover:underline mt-2 inline-block"
              >
                Read more →
              </a>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function RecentLogsSection() {
  const { data: logsData, isLoading, error } = useRecentLogs(10);

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Recent Activity</h2>
        <Link
          to="/logs"
          className="text-sm text-trig-green-600 hover:text-trig-green-700 hover:underline"
        >
          View all logs →
        </Link>
      </div>
      {error ? (
        <p className="text-red-600">Failed to load recent logs</p>
      ) : (
        <LogList
          logs={logsData?.items || []}
          isLoading={isLoading}
          emptyMessage="No recent activity"
        />
      )}
    </Card>
  );
}

export default function Home() {
  return (
    <Layout>
      <div className="flex flex-col-reverse lg:flex-row gap-6">
        {/* Sidebar - bottom on mobile, left on desktop */}
        <Sidebar />

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          <WelcomeSection />
          <SiteStatsSection />
          <NewsSection />
          <RecentLogsSection />
        </div>
      </div>
    </Layout>
  );
}
