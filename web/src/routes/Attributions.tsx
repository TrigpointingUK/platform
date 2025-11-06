import { useEffect, useState } from "react";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";

interface Attribution {
  name: string;
  version: string;
  license: string;
  repository: string;
  author: string;
  description: string;
  type: "npm" | "python";
}

interface AttributionsData {
  generatedAt: string;
  npm: Attribution[];
  python: Attribution[];
  summary: {
    total: number;
    npm: number;
    python: number;
  };
}

export default function Attributions() {
  const [data, setData] = useState<AttributionsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<"all" | "npm" | "python">("all");
  const [filterLicense, setFilterLicense] = useState<string>("all");

  useEffect(() => {
    fetch("/attributions.json")
      .then((res) => {
        if (!res.ok) throw new Error("Attributions data not found");
        return res.json();
      })
      .then((data) => setData(data))
      .catch((err) => setError(err.message));
  }, []);

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString("en-GB", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  };

  const getFilteredDependencies = () => {
    if (!data) return [];

    let deps: Attribution[] = [];
    
    if (filterType === "all") {
      deps = [...data.npm, ...data.python];
    } else if (filterType === "npm") {
      deps = data.npm;
    } else {
      deps = data.python;
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      deps = deps.filter(
        (dep) =>
          dep.name.toLowerCase().includes(term) ||
          dep.license.toLowerCase().includes(term) ||
          dep.author.toLowerCase().includes(term)
      );
    }

    // Filter by license
    if (filterLicense !== "all") {
      deps = deps.filter((dep) => dep.license === filterLicense);
    }

    return deps.sort((a, b) => a.name.localeCompare(b.name));
  };

  const getUniqueLicenses = () => {
    if (!data) return [];
    const licenses = new Set<string>();
    [...data.npm, ...data.python].forEach((dep) => {
      if (dep.license && dep.license !== "Unknown") {
        licenses.add(dep.license);
      }
    });
    return Array.from(licenses).sort();
  };

  const getLicenseBadgeColor = (license: string) => {
    const licenseLower = license.toLowerCase();
    // MIT and similar permissive licenses
    if (licenseLower.includes("mit") || licenseLower.includes("isc")) {
      return "bg-green-100 text-green-800";
    }
    // Apache licenses
    if (licenseLower.includes("apache")) {
      return "bg-blue-100 text-blue-800";
    }
    // BSD licenses
    if (licenseLower.includes("bsd")) {
      return "bg-purple-100 text-purple-800";
    }
    // GPL licenses
    if (licenseLower.includes("gpl") && !licenseLower.includes("agpl")) {
      return "bg-yellow-100 text-yellow-800";
    }
    // AGPL
    if (licenseLower.includes("agpl")) {
      return "bg-orange-100 text-orange-800";
    }
    // Creative Commons licenses
    if (licenseLower.includes("creative commons") || licenseLower.includes("cc-") || licenseLower.includes("cc by")) {
      return "bg-indigo-100 text-indigo-800";
    }
    // Unlicense / Public Domain
    if (licenseLower.includes("unlicense") || licenseLower.includes("public domain")) {
      return "bg-teal-100 text-teal-800";
    }
    // Unknown
    if (licenseLower.includes("unknown")) {
      return "bg-gray-100 text-gray-600";
    }
    // Default
    return "bg-gray-100 text-gray-800";
  };

  if (error) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">
            Open Source Attributions
          </h1>
          <Card>
            <p className="text-red-600">
              Unable to load attribution data: {error}
            </p>
            <p className="text-gray-600 mt-4 text-sm">
              Attribution data is generated during the build process. If you're
              running in development, you may need to run:{" "}
              <code className="bg-gray-100 px-2 py-1 rounded">
                node generate-attributions.mjs
              </code>
            </p>
          </Card>
        </div>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">
            Open Source Attributions
          </h1>
          <Card>
            <p className="text-gray-600">Loading attribution data...</p>
          </Card>
        </div>
      </Layout>
    );
  }

  const filteredDeps = getFilteredDependencies();
  const uniqueLicenses = getUniqueLicenses();

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          Open Source Attributions
        </h1>
        <p className="text-gray-600 mb-6">
          This page lists all open source packages used in this application,
          along with their licenses and attribution information.
        </p>

        {/* Summary Card */}
        <Card className="mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">Total Packages</dt>
              <dd className="mt-1 text-2xl font-bold text-gray-900">
                {data.summary.total}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">NPM Packages</dt>
              <dd className="mt-1 text-2xl font-bold text-blue-600">
                {data.summary.npm}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Python Packages</dt>
              <dd className="mt-1 text-2xl font-bold text-green-600">
                {data.summary.python}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {formatDate(data.generatedAt)}
              </dd>
            </div>
          </div>
        </Card>

        {/* Filters */}
        <Card className="mb-6">
          <div className="space-y-4">
            <div>
              <label
                htmlFor="search"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Search Packages
              </label>
              <input
                id="search"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name, license, or author..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-trig-green-500 focus:border-transparent"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="type-filter"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Package Type
                </label>
                <select
                  id="type-filter"
                  value={filterType}
                  onChange={(e) =>
                    setFilterType(e.target.value as "all" | "npm" | "python")
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-trig-green-500 focus:border-transparent"
                >
                  <option value="all">All Types</option>
                  <option value="npm">NPM Packages</option>
                  <option value="python">Python Packages</option>
                </select>
              </div>
              <div>
                <label
                  htmlFor="license-filter"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  License
                </label>
                <select
                  id="license-filter"
                  value={filterLicense}
                  onChange={(e) => setFilterLicense(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-trig-green-500 focus:border-transparent"
                >
                  <option value="all">All Licenses</option>
                  {uniqueLicenses.map((license) => (
                    <option key={license} value={license}>
                      {license}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {filteredDeps.length !== data.summary.total && (
              <p className="text-sm text-gray-600">
                Showing {filteredDeps.length} of {data.summary.total} packages
              </p>
            )}
          </div>
        </Card>

        {/* Dependencies List */}
        <div className="space-y-4">
          {filteredDeps.length === 0 ? (
            <Card>
              <p className="text-gray-600 text-center py-8">
                No packages found matching your filters.
              </p>
            </Card>
          ) : (
            filteredDeps.map((dep) => (
              <Card key={`${dep.type}-${dep.name}`}>
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-semibold text-gray-900">
                        {dep.name}
                      </h3>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          dep.type === "npm"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-green-100 text-green-800"
                        }`}
                      >
                        {dep.type.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-500 font-mono">
                        v{dep.version}
                      </span>
                    </div>
                    {dep.description && (
                      <p className="text-gray-600 text-sm mb-3">
                        {dep.description}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      <div>
                        <span className="text-gray-500">License:</span>{" "}
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${getLicenseBadgeColor(
                            dep.license
                          )}`}
                        >
                          {dep.license}
                        </span>
                      </div>
                      {dep.author !== "Unknown" && (
                        <div>
                          <span className="text-gray-500">Author:</span>{" "}
                          <span className="text-gray-900">{dep.author}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    {dep.repository && (
                      <a
                        href={dep.repository}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-4 py-2 bg-trig-green-600 text-white rounded-lg hover:bg-trig-green-700 transition-colors text-sm font-medium"
                      >
                        View Package →
                      </a>
                    )}
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* License Notice */}
        <Card className="mt-8 bg-gray-50">
          <h2 className="text-xl font-bold text-gray-800 mb-3">
            License Notice
          </h2>
          <p className="text-gray-700 text-sm leading-relaxed">
            This application uses open source software. Each package listed above
            is provided under its respective license. Please refer to the
            individual package repositories for full license text and terms. 
            TrigpointingUK would like to express its sincere gratitude to all open source
            developers the world over.
          </p>
          <p className="text-gray-700 text-sm mt-3">
            For questions or concerns about open source licensing, please{" "}
            <a
              href="/contact"
              className="text-trig-green-600 hover:text-trig-green-700 underline"
            >
              contact us
            </a>
            .
          </p>
        </Card>
      </div>
    </Layout>
  );
}

