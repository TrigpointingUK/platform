import { Link } from "react-router-dom";

import Sidebar from "../components/layout/Sidebar";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import LogList from "../components/logs/LogList";
import { useSiteStats } from "../hooks/useSiteStats";
import { useRecentLogs } from "../hooks/useRecentLogs";
import { useNews } from "../hooks/useNews";
import { useUserProfile } from "../hooks/useUserProfile";
import { getCanonicalOrigin } from "../lib/canonicalOrigin";

function WelcomeSection() {
  return (
    <Card className="mb-6">
      {/* Small screens: image beside heading only */}
      <div className="flex items-center gap-4 mb-4 sm:hidden">
        <h1 className="text-4xl font-bold text-trig-green-600 dark:text-trig-green-400 flex-1 min-w-0">
          Welcome to TrigpointingUK
        </h1>
        <picture className="flex-shrink-0">
          <source srcSet="/img/flush-bracket.webp" type="image/webp" />
          <img
            src="/img/flush-bracket.apng"
            alt="Rotating 3D model of an Ordnance Survey flush bracket"
            className="w-24 h-24 object-contain"
            width={96}
            height={96}
            fetchPriority="high"
          />
        </picture>
      </div>
      {/* Larger screens: image as full column beside all content */}
      <div className="hidden sm:flex items-center gap-6">
        <div className="flex-1 min-w-0">
          <h1 className="text-4xl font-bold text-trig-green-600 dark:text-trig-green-400 mb-4">
            Welcome to TrigpointingUK
          </h1>
          <p className="text-lg text-gray-700 dark:text-gray-300 mb-4">
            The UK's premier resource for trig points, triangulation pillars
            and survey markers. Find trig points near you, log your visits,
            and join thousands of enthusiasts exploring Britain's geodetic
            heritage.
          </p>
          <div className="flex gap-3 flex-wrap w-full">
            <Button variant="primary" className="flex-1 min-w-[140px]">
              <Link
                to="/trigs"
                className="block w-full text-center text-current"
              >
                Trig Points Near Me
              </Link>
            </Button>
            <Button variant="primary" className="flex-1 min-w-[140px]">
              <Link to="/map" className="block w-full text-center text-current">
                Map
              </Link>
            </Button>
          </div>
        </div>
        <picture className="flex-shrink-0">
          <source srcSet="/img/flush-bracket.webp" type="image/webp" />
          <img
            src="/img/flush-bracket.apng"
            alt="Rotating 3D model of an Ordnance Survey flush bracket"
            className="w-32 h-32 md:w-40 md:h-40 object-contain"
            width={160}
            height={160}
            fetchPriority="high"
          />
        </picture>
      </div>
      {/* Description and buttons below heading on small screens */}
      <div className="sm:hidden">
        <p className="text-lg text-gray-700 dark:text-gray-300 mb-4">
          The UK's premier resource for trig points, triangulation pillars
          and survey markers. Find trig points near you, log your visits,
          and join thousands of enthusiasts exploring Britain's geodetic
          heritage.
        </p>
        <div className="flex gap-3 flex-wrap w-full">
          <Button variant="primary" className="flex-1 min-w-[140px]">
            <Link
              to="/trigs"
              className="block w-full text-center text-current"
            >
              Trig Points Near Me
            </Link>
          </Button>
          <Button variant="primary" className="flex-1 min-w-[140px]">
            <Link to="/map" className="block w-full text-center text-current">
              Map
            </Link>
          </Button>
        </div>
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
          <h2 className="text-2xl font-bold text-trig-green-600 inline">Database Entries</h2>
          <span className="text-sm font-normal text-gray-600 dark:text-gray-400 ml-2">(Click to browse)</span>
        </div>
        <p className="text-red-600 dark:text-red-400">Failed to load statistics</p>
      </Card>
    );
  }

  if (isLoading || !stats) {
    return (
      <Card className="mb-6">
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-trig-green-600 inline">Database Entries</h2>
          <span className="text-sm font-normal text-gray-600 dark:text-gray-400 ml-2">(Click to browse)</span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="flex justify-center items-center h-12 mb-2">
                <div className="h-12 w-12 bg-gray-200 dark:bg-gray-600 rounded" />
              </div>
              <div className="h-8 w-20 bg-gray-200 dark:bg-gray-600 rounded mx-auto mb-1" />
              <div className="h-4 w-16 bg-gray-200 dark:bg-gray-600 rounded mx-auto" />
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600 flex justify-center animate-pulse">
          <div className="h-4 w-64 bg-gray-200 dark:bg-gray-600 rounded" />
        </div>
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
      label: "Members",
      value: stats.total_members.toLocaleString(),
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
        <h2 className="text-2xl font-bold text-trig-green-600 inline">Database Entries</h2>
        <span className="text-sm font-normal text-gray-600 dark:text-gray-400 ml-2">(Click to browse)</span>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statItems.map((item) => (
          <Link
            key={item.label}
            to={item.link}
            className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors block"
          >
            <div className="text-3xl mb-2 flex justify-center items-center h-12">
              {item.isImage ? (
                <img 
                  src={item.icon} 
                  alt={item.label} 
                  className="h-12 w-12 object-contain"
                  width={48}
                  height={48}
                />
              ) : (
                <span>{item.icon}</span>
              )}
            </div>
            <div className={`text-3xl font-bold ${item.color} mb-1`}>
              {item.value}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-300">{item.label}</div>
          </Link>
        ))}
      </div>
      {stats.recent_logs_7d > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600 text-sm text-gray-600 dark:text-gray-400 text-center">
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
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">Recent Site News</h2>
        <div className="space-y-4 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="border-l-4 border-gray-200 dark:border-gray-600 pl-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="h-5 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
                  <div className="h-4 w-full max-w-sm bg-gray-200 dark:bg-gray-700 rounded mt-2" />
                </div>
                <div className="h-3 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (!news || news.length === 0) {
    return null;
  }

  return (
    <Card className="mb-6">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">Recent Site News</h2>
      <div className="space-y-4">
        {news.slice(0, 3).map((item) => (
          <div key={item.id} className="border-l-4 border-trig-green-600 pl-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 dark:text-gray-100">{item.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{item.summary}</p>
              </div>
              <time className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
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
  const { data: userProfile } = useUserProfile("me");
  const showTrigCondition = userProfile?.prefs?.ui_prefs?.show_trig_condition ?? false;

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Recent Activity</h2>
        <Link
          to="/logs"
          className="text-sm text-trig-green-600 hover:text-trig-green-700 hover:underline"
        >
          View all logs →
        </Link>
      </div>
      {error ? (
        <p className="text-red-600 dark:text-red-400">Failed to load recent logs</p>
      ) : (
        <LogList
          logs={logsData?.items || []}
          isLoading={isLoading}
          emptyMessage="No recent activity"
          showTrigCondition={showTrigCondition}
          currentUserId={userProfile?.id}
        />
      )}
    </Card>
  );
}

export default function Home() {
  const origin = getCanonicalOrigin();
  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "TrigpointingUK",
    "alternateName": "Trigpointing UK",
    "url": origin,
    "description":
      "Find trig points near you — the UK's premier resource for triangulation pillars and survey markers. Browse over 17,000 trig points with photos, maps, and visit logs.",
    "potentialAction": {
      "@type": "SearchAction",
      "target": `${origin}/trigs?location={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };

  return (
    <>
      <title>TrigpointingUK — Find Trig Points Near You</title>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
      />
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
    </>
  );
}
