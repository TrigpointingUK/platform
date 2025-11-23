import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import {
  USERS_SORT_OPTIONS,
  UserSortDirection,
  UserSortOption,
  useUsersDirectory,
} from "../hooks/useUsersDirectory";

function formatMemberSince(value?: string | null) {
  if (!value) {
    return "Joined date unknown";
  }
  return new Date(value).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });
}

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sort, setSort] = useState<UserSortOption>("trigs");
  const [direction, setDirection] = useState<UserSortDirection>("desc");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const {
    data,
    isLoading,
    isError,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useUsersDirectory({
    query: debouncedSearch,
    sort,
    direction,
  });

  const users = useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data]
  );
  const totalCount = data?.pages[0]?.total ?? 0;

  const sentinelRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) {
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (
          entries[0]?.isIntersecting &&
          hasNextPage &&
          !isFetchingNextPage
        ) {
          fetchNextPage();
        }
      },
      { rootMargin: "320px" }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  const resultSummary = useMemo(() => {
    if (isLoading) {
      return "Loading members…";
    }
    if (users.length === 0) {
      return "No members match your filters";
    }
    const prefix = debouncedSearch
      ? "Matching members"
      : "Community members";
    return `${prefix}: ${users.length.toLocaleString("en-GB")} of ${totalCount.toLocaleString(
      "en-GB"
    )}`;
  }, [debouncedSearch, isLoading, totalCount, users.length]);

  const toggleDirection = () =>
    setDirection((prev) => (prev === "desc" ? "asc" : "desc"));

  return (
    <Layout>
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-trig-green-600 font-semibold">
            Community
          </p>
          <h1 className="text-3xl font-bold text-gray-900">
            Trigpointing members
          </h1>
          <p className="text-gray-600 max-w-2xl">
            Browse the people behind the logs. Sort by trigpoints, photos, or
            joined date and quickly jump to a specific profile.
          </p>
        </div>

        <Card className="shadow-sm border border-gray-100">
          <div className="flex flex-col gap-4 md:flex-row md:items-end">
            <div className="flex-1">
              <label
                htmlFor="user-search"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Find a user
              </label>
              <div className="relative">
                <input
                  id="user-search"
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Start typing a username…"
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-base shadow-inner-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500 hover:text-gray-800"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <div>
                <label
                  htmlFor="user-sort"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Sort by
                </label>
                <select
                  id="user-sort"
                  value={sort}
                  onChange={(event) =>
                    setSort(event.target.value as UserSortOption)
                  }
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500"
                >
                  {USERS_SORT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <span className="block text-sm font-medium text-gray-700 mb-2">
                  Direction
                </span>
                <button
                  type="button"
                  onClick={toggleDirection}
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-gray-50 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500"
                >
                  {direction === "desc" ? "Descending" : "Ascending"}
                  <span aria-hidden="true">
                    {direction === "desc" ? "↓" : "↑"}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </Card>

        <div className="flex items-center justify-between flex-wrap gap-3">
          <p className="text-sm text-gray-600">{resultSummary}</p>
          {debouncedSearch && (
            <span className="text-xs uppercase tracking-wide text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              Filtered by “{debouncedSearch}”
            </span>
          )}
        </div>

        {isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error instanceof Error
              ? error.message
              : "Unable to load members right now."}
          </div>
        )}

        {isLoading && (
          <div className="flex flex-col items-center gap-4 py-16">
            <Spinner size="lg" />
            <p className="text-gray-600">Loading the community directory…</p>
          </div>
        )}

        {!isLoading && users.length === 0 && (
          <Card className="text-center py-12">
            <p className="text-4xl mb-3">🧭</p>
            <p className="text-lg font-semibold mb-1 text-gray-900">
              No matches found
            </p>
            <p className="text-gray-600">
              Try a different search term or change the sort order.
            </p>
          </Card>
        )}

        {users.length > 0 && (
          <div className="space-y-4">
            {users.map((user) => (
              <Link to={user.profile_path} key={user.id}>
                <Card className="p-0 transition-shadow hover:shadow-lg">
                  <div className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:gap-6">
                    <div className="flex-1">
                      <p className="text-2xl font-bold text-gray-900">
                        {user.name}
                      </p>
                    </div>
                    <div className="text-sm text-gray-600 lg:text-center lg:min-w-[170px]">
                      <p className="uppercase tracking-wide text-gray-500 text-xs mb-1">
                        Member since
                      </p>
                      <p className="font-medium text-gray-900">
                        {formatMemberSince(user.member_since)}
                      </p>
                    </div>
                    <div className="flex flex-1 flex-wrap gap-3 justify-start lg:justify-end">
                      <StatPill
                        label="Trigpoints"
                        value={user.stats.total_trigs_logged}
                      />
                      <StatPill
                        label="Photos"
                        value={user.stats.total_photos}
                      />
                      <StatPill label="Logs" value={user.stats.total_logs} />
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {hasNextPage && <div ref={sentinelRef} className="h-px w-full" />}

        {isFetchingNextPage && (
          <div className="flex flex-col items-center gap-3 py-6 text-gray-600">
            <Spinner size="sm" />
            <span>Loading more members…</span>
          </div>
        )}
      </div>
    </Layout>
  );
}

interface StatPillProps {
  label: string;
  value: number;
}

function StatPill({ label, value }: StatPillProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-center">
      <p className="text-xl font-semibold text-trig-green-700 leading-tight">
        {value.toLocaleString("en-GB")}
      </p>
      <p className="text-[0.7rem] uppercase tracking-wide text-gray-500">
        {label}
      </p>
    </div>
  );
}


