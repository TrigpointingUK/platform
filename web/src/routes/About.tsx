import { useEffect, useState } from "react";
import Card from "../components/ui/Card";

interface BuildInfo {
  version: string;
  commitSha: string;
  commitShort: string;
  branch: string;
  commitMessage: string;
  buildTime: string;
  nodeVersion: string;
  githubRun: string | null;
  githubRunNumber: string | null;
  githubActor: string | null;
  githubWorkflow: string | null;
  githubRef: string | null;
  environment: string;
}

export default function About() {
  const [buildInfo, setBuildInfo] = useState<BuildInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/buildInfo.json")
      .then((res) => {
        if (!res.ok) throw new Error("Build info not found");
        return res.json();
      })
      .then((data) => setBuildInfo(data))
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
      second: "2-digit",
      timeZoneName: "short",
    });
  };

  const getGitHubLink = () => {
    if (!buildInfo?.commitSha) return null;
    // Adjust this URL to your actual GitHub repository
    return `https://github.com/TrigpointingUK/platform/commit/${buildInfo.commitSha}`;
  };

  const getGitHubRunLink = () => {
    if (!buildInfo?.githubRun) return null;
    return `https://github.com/TrigpointingUK/platform/actions/runs/${buildInfo.githubRun}`;
  };

  if (error) {
    return (
      <>
        <title>About | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-6">About</h1>
          <Card>
            <p className="text-red-600 dark:text-red-400">
              Unable to load build information: {error}
            </p>
          </Card>
        </div>
      </>
    );
  }

  if (!buildInfo) {
    return (
      <>
        <title>About | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-6">About</h1>
          <Card>
            <p className="text-gray-600 dark:text-gray-400">Loading build information...</p>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <title>About | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-6">About Trigpointing UK</h1>

        <div className="space-y-6">
          {/* Build Information */}
          <Card>
            <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
              Build Information
            </h2>
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Version</dt>
                  <dd className="mt-1 text-lg font-mono text-gray-900 dark:text-gray-100">
                    {buildInfo.version}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Environment</dt>
                  <dd className="mt-1">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        buildInfo.environment === "production"
                          ? "bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300"
                          : buildInfo.environment === "staging"
                          ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300"
                          : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                      }`}
                    >
                      {buildInfo.environment}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Build Time</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                    {formatDate(buildInfo.buildTime)}
                  </dd>
                </div>
              </div>
            </div>
          </Card>

          {/* Git Information */}
          <Card>
            <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
              Git Information
            </h2>
            <div className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Commit</dt>
                <dd className="mt-1 flex items-center gap-2">
                  <code className="text-sm font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-900 dark:text-gray-100">
                    {buildInfo.commitShort}
                  </code>
                  {getGitHubLink() && (
                    <a
                      href={getGitHubLink()!}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 text-sm hover:underline"
                    >
                      View on GitHub →
                    </a>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Branch</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{buildInfo.branch}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Commit Message</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
                  {buildInfo.commitMessage}
                </dd>
              </div>
            </div>
          </Card>

          {/* GitHub Actions Information */}
          {buildInfo.githubRun && (
            <Card>
              <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
                CI/CD Information
              </h2>
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Workflow</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                      {buildInfo.githubWorkflow}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Run Number</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                      #{buildInfo.githubRunNumber}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Built By</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                      {buildInfo.githubActor}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Reference</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                      {buildInfo.githubRef}
                    </dd>
                  </div>
                </div>
                {getGitHubRunLink() && (
                  <div className="pt-2">
                    <a
                      href={getGitHubRunLink()!}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 hover:underline"
                    >
                      View GitHub Actions Run →
                    </a>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Technical Details */}
          <Card>
            <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
              Technical Details
            </h2>
            <div className="space-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Node Version</dt>
                <dd className="mt-1 text-sm font-mono text-gray-900 dark:text-gray-100">
                  {buildInfo.nodeVersion}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Full Commit SHA</dt>
                <dd className="mt-1 text-xs font-mono text-gray-600 dark:text-gray-400 break-all">
                  {buildInfo.commitSha}
                </dd>
              </div>
            </div>
          </Card>

          {/* About Project */}
          <Card>
            <h2 className="text-2xl font-bold text-trig-green-600 mb-4">
              About This Project
            </h2>
            <div className="prose prose-sm max-w-none">
              <p className="text-gray-700 dark:text-gray-300">
                Trigpointing UK is a comprehensive database and community platform for
                triangulation pillars and survey markers across the United Kingdom.
              </p>
              <p className="text-gray-700 dark:text-gray-300 mt-3">
                This modern React-based single-page application provides a responsive,
                mobile-friendly interface for browsing trigpoints, viewing photos, and
                logging visits.
              </p>
              <div className="mt-4">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                  Technology Stack
                </h3>
                <ul className="list-disc list-inside text-gray-700 dark:text-gray-300 space-y-1">
                  <li>React 18 with TypeScript</li>
                  <li>Tailwind CSS v4 for styling</li>
                  <li>Vite for fast builds</li>
                  <li>TanStack Query for data fetching</li>
                  <li>Auth0 for authentication</li>
                  <li>FastAPI backend</li>
                </ul>
              </div>
              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <a
                  href="/attributions"
                  className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 font-medium hover:underline"
                >
                  View Open Source Attributions →
                </a>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  See all open source packages used in this application with
                  their licenses and attribution information.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

