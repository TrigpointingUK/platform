import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import {
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

  const handleSortClick = (field: UserSortOption) => {
    if (sort === field) {
      setDirection((prev) => (prev === "desc" ? "asc" : "desc"));
      return;
    }
    setSort(field);
    setDirection(field === "name" ? "asc" : "desc");
  };

  const renderHeaderCell = (
    label: string,
    field?: UserSortOption,
    alignment: "left" | "center" = "left"
  ) => {
    const alignClass =
      alignment === "center"
        ? "justify-center text-center"
        : "justify-start text-left";

    if (!field) {
      return (
        <span
          className={`flex items-center gap-1 uppercase tracking-wide text-xs font-semibold text-gray-500 ${alignClass}`}
        >
          {label}
        </span>
      );
    }

    const isActive = sort === field;
    const ariaSort = isActive
      ? direction === "desc"
        ? "descending"
        : "ascending"
      : "none";
    const icon = direction === "desc" ? "▼" : "▲";

    return (
      <button
        type="button"
        onClick={() => handleSortClick(field)}
        className={`flex items-center gap-1 uppercase tracking-wide text-xs font-semibold transition-colors ${alignClass} ${
          isActive ? "text-trig-green-700" : "text-gray-500 hover:text-trig-green-600"
        }`}
        role="columnheader"
        aria-sort={ariaSort}
      >
        <span>{label}</span>
        {isActive && (
          <span aria-hidden="true" className="text-[0.6rem] leading-none">
            {icon}
          </span>
        )}
      </button>
    );
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
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
          <div>
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
        </Card>

        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <p className="text-sm text-gray-600">{resultSummary}</p>
          {debouncedSearch && (
            <span className="text-xs uppercase tracking-wide text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              Filtered by "{debouncedSearch}"
            </span>
          )}
        </div>

        {/* Mobile sort controls (non-sticky) */}
        <Card className="sm:hidden shadow-sm border border-gray-100 mb-4">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Sort by
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleSortClick("name")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  sort === "name"
                    ? "bg-trig-green-50 border-trig-green-600 text-trig-green-700"
                    : "bg-white border-gray-300 text-gray-700 hover:border-trig-green-500"
                }`}
              >
                Name {sort === "name" && (direction === "desc" ? "▼" : "▲")}
              </button>
              <button
                type="button"
                onClick={() => handleSortClick("joined")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  sort === "joined"
                    ? "bg-trig-green-50 border-trig-green-600 text-trig-green-700"
                    : "bg-white border-gray-300 text-gray-700 hover:border-trig-green-500"
                }`}
              >
                Joined {sort === "joined" && (direction === "desc" ? "▼" : "▲")}
              </button>
              <button
                type="button"
                onClick={() => handleSortClick("trigs")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  sort === "trigs"
                    ? "bg-trig-green-50 border-trig-green-600 text-trig-green-700"
                    : "bg-white border-gray-300 text-gray-700 hover:border-trig-green-500"
                }`}
              >
                Trigpoints {sort === "trigs" && (direction === "desc" ? "▼" : "▲")}
              </button>
              <button
                type="button"
                onClick={() => handleSortClick("photos")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  sort === "photos"
                    ? "bg-trig-green-50 border-trig-green-600 text-trig-green-700"
                    : "bg-white border-gray-300 text-gray-700 hover:border-trig-green-500"
                }`}
              >
                Photos {sort === "photos" && (direction === "desc" ? "▼" : "▲")}
              </button>
              <button
                type="button"
                onClick={() => handleSortClick("logs")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  sort === "logs"
                    ? "bg-trig-green-50 border-trig-green-600 text-trig-green-700"
                    : "bg-white border-gray-300 text-gray-700 hover:border-trig-green-500"
                }`}
              >
                Logs {sort === "logs" && (direction === "desc" ? "▼" : "▲")}
              </button>
            </div>
          </div>
        </Card>

        <div className="sticky top-16 z-40 bg-white border-b border-gray-200 shadow-sm hidden sm:block">
          <div className="px-4 py-3">
            <div className="grid grid-cols-2 gap-4 text-xs font-semibold uppercase tracking-wide text-gray-500 sm:grid-cols-[2fr_1.2fr_repeat(3,minmax(0,1fr))]">
              {renderHeaderCell("Name", "name")}
              {renderHeaderCell("Member since", "joined")}
              {renderHeaderCell("Trigpoints", "trigs", "center")}
              {renderHeaderCell("Photos", "photos", "center")}
              {renderHeaderCell("Logs", "logs", "center")}
            </div>
          </div>
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
          <div className="space-y-0.5">
            {users.map((user) => (
              <Card className="p-0 transition-shadow hover:shadow-md" key={user.id}>
                <div className="px-3 py-2 sm:py-0.5">
                  {/* Mobile layout */}
                  <div className="sm:hidden space-y-2">
                    <div className="flex flex-wrap justify-between items-baseline gap-x-3 gap-y-1">
                      <Link
                        to={user.profile_path}
                        className="text-left text-[0.95rem] font-semibold text-gray-900 leading-tight hover:text-trig-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500"
                      >
                        {user.name}
                      </Link>
                      <Link
                        to={user.profile_path}
                        className="text-right text-[0.8rem] text-gray-600 leading-tight hover:text-trig-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500 rounded whitespace-nowrap"
                      >
                        <span className="text-gray-500">Member Since:</span>{" "}
                        <span className="font-medium text-gray-900">
                          {formatMemberSince(user.member_since)}
                        </span>
                      </Link>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <CountCell
                        label="Trigpoints"
                        value={user.stats.total_trigs_logged}
                        to={`${user.profile_path}/logs`}
                      />
                      <CountCell
                        label="Photos"
                        value={user.stats.total_photos}
                        to={`${user.profile_path}/photos`}
                      />
                      <CountCell
                        label="Logs"
                        value={user.stats.total_logs}
                        to={`${user.profile_path}/logs`}
                      />
                    </div>
                  </div>

                  {/* Desktop layout */}
                  <div className="hidden sm:grid gap-0.5 text-[0.95rem] text-gray-700 sm:grid-cols-[2fr_1.2fr_repeat(3,minmax(0,1fr))] sm:items-center leading-tight">
                    <Link
                      to={user.profile_path}
                      className="text-left text-[0.95rem] font-semibold text-gray-900 leading-tight hover:text-trig-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500"
                    >
                      {user.name}
                    </Link>
                    <Link
                      to={user.profile_path}
                      className="text-gray-600 leading-tight hover:text-trig-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500 rounded"
                    >
                      <p className="font-medium text-gray-900 leading-tight">
                        {formatMemberSince(user.member_since)}
                      </p>
                    </Link>
                    <CountCell
                      label="Trigpoints"
                      value={user.stats.total_trigs_logged}
                      to={`${user.profile_path}/logs`}
                    />
                    <CountCell
                      label="Photos"
                      value={user.stats.total_photos}
                      to={`${user.profile_path}/photos`}
                    />
                    <CountCell
                      label="Logs"
                      value={user.stats.total_logs}
                      to={`${user.profile_path}/logs`}
                    />
                  </div>
                </div>
              </Card>
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

interface CountCellProps {
  label: string;
  value: number;
  to: string;
}

function CountCell({ label, value, to }: CountCellProps) {
  return (
    <Link
      to={to}
      className="text-center leading-snug hover:text-trig-green-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500 rounded"
    >
      <p className="text-[0.6rem] uppercase tracking-wide text-gray-500 leading-tight">
        {label}
      </p>
      <p className="text-base font-semibold text-trig-green-700 leading-snug">
        {value.toLocaleString("en-GB")}
      </p>
    </Link>
  );
}
