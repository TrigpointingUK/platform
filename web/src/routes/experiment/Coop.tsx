/**
 * Co-op Trigpointing experiment page.
 *
 * Lets users select a group of members and compare which trigpoints each has
 * (or hasn't) visited, in a grid sorted by distance from a chosen location.
 */

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import {
  FlaskConical,
  Users,
  MapPin,
  X,
  Search,
  ChevronDown,
  ArrowLeft,
  Loader2,
} from "lucide-react";

import Card from "../../components/ui/Card";
import { LocationSearch } from "../../components/trigs/LocationSearch";
import { DistanceFilter } from "../../components/trigs/DistanceFilter";
import { StatusFilter } from "../../components/trigs/StatusFilter";
import AddToListButton from "../../components/lists/AddToListButton";
import { useUserProfile } from "../../hooks/useUserProfile";
import { useUserSearch } from "../../hooks/useUserSearch";
import { useCoopData, type CoopFilterMode } from "../../hooks/useCoopData";
import { useConditionInfo } from "../../hooks/useConditionInfo";

const DEFAULT_LAT = 53.2585;
const DEFAULT_LON = -1.9106;
const DEFAULT_LOCATION_NAME = "Buxton";
const DEFAULT_MAX_KM = 50;
const MAX_USERS = 8;

const ALL_STATUSES = [10, 20, 30, 40, 50, 60];
const STATUS_ID_TO_CATEGORY_CODE: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

const FILTER_MODE_LABELS: Record<CoopFilterMode, string> = {
  all: "All trigs",
  visited_by_me: "Visited by me",
  unvisited_by_me: "Not visited by me",
  only_visited_by_me: "Only visited by me",
  visited_by_all_except_me: "Visited by everyone except me",
  unvisited_by_all: "Not visited by anyone",
  visited_by_any: "Visited by anyone",
  not_visited_by_most: "Not visited by most",
  visited_by_most: "Visited by most",
  visited_by_all: "Visited by everyone",
};

interface SelectedUser {
  id: number;
  name: string;
}

function calculateBearing(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const lat1Rad = (lat1 * Math.PI) / 180;
  const lat2Rad = (lat2 * Math.PI) / 180;
  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x =
    Math.cos(lat1Rad) * Math.sin(lat2Rad) -
    Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  const bearing = (Math.atan2(y, x) * 180) / Math.PI;
  return (bearing + 360) % 360;
}

function BearingArrow({ bearing }: { bearing: number }) {
  return (
    <div
      className="text-gray-500 dark:text-gray-400"
      title={`Bearing: ${bearing.toFixed(0)}°`}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="currentColor"
        style={{ transform: `rotate(${bearing}deg)` }}
      >
        <path d="M12 2l-4 9h3v11h2V11h3z" />
      </svg>
    </div>
  );
}

function formatDistance(km: number, unit: "K" | "M" = "K"): string {
  if (unit === "M") {
    const miles = km * 0.621371;
    return `${miles.toFixed(1)} mi`;
  }
  return `${km.toFixed(1)} km`;
}

function UserSearchPanel({
  selectedUsers,
  onAddUser,
  onRemoveUser,
  currentUserId,
}: {
  selectedUsers: SelectedUser[];
  onAddUser: (user: SelectedUser) => void;
  onRemoveUser: (userId: number) => void;
  currentUserId: number | undefined;
}) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { data: results, isLoading } = useUserSearch(query, isOpen);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedIds = useMemo(
    () => new Set(selectedUsers.map((u) => u.id)),
    [selectedUsers],
  );

  const filteredResults = results?.filter((r) => !selectedIds.has(r.id));

  return (
    <div className="space-y-3">
      <div className="relative" ref={dropdownRef}>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="Search for a member to add..."
            disabled={selectedUsers.length >= MAX_USERS}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-trig-green-500 focus:border-transparent bg-white dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {isOpen && query.length >= 2 && (
          <div className="absolute z-20 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {isLoading && (
              <div className="px-4 py-3 text-gray-500 dark:text-gray-400 text-center text-sm">
                Searching...
              </div>
            )}
            {!isLoading && filteredResults && filteredResults.length === 0 && (
              <div className="px-4 py-3 text-gray-500 dark:text-gray-400 text-center text-sm">
                No members found
              </div>
            )}
            {!isLoading &&
              filteredResults &&
              filteredResults.map((user) => (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => {
                    onAddUser({ id: user.id, name: user.name });
                    setQuery("");
                    setIsOpen(false);
                  }}
                  className="w-full px-4 py-2.5 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0"
                >
                  <div className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                    {user.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {user.stats.total_trigs_logged} trigs logged
                  </div>
                </button>
              ))}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {selectedUsers.map((user) => {
          const isCurrentUser = user.id === currentUserId;
          return (
            <span
              key={user.id}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${
                isCurrentUser
                  ? "bg-trig-green-100 dark:bg-trig-green-900/30 text-trig-green-800 dark:text-trig-green-300"
                  : "bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300"
              }`}
            >
              <Link
                to={`/profile/${user.id}`}
                className="hover:underline"
              >
                {user.name}
              </Link>
              {isCurrentUser && (
                <span className="text-xs opacity-70">(you)</span>
              )}
              {!isCurrentUser && (
                <button
                  type="button"
                  onClick={() => onRemoveUser(user.id)}
                  className="ml-0.5 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                  title={`Remove ${user.name}`}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </span>
          );
        })}
      </div>

      {selectedUsers.length >= MAX_USERS && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Maximum of {MAX_USERS} members reached.
        </p>
      )}
    </div>
  );
}

function CoopGrid({
  data,
  centerLat,
  centerLon,
  distanceUnit,
  showListActions,
  getConditionInfo,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
}: {
  data: ReturnType<typeof useCoopData>["data"];
  centerLat: number;
  centerLon: number;
  distanceUnit: "K" | "M";
  showListActions: boolean;
  getConditionInfo: ReturnType<
    typeof useConditionInfo
  >["getConditionInfo"];
  hasNextPage: boolean | undefined;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
}) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sentinelRef.current || !hasNextPage) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { rootMargin: "200px" },
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const users = useMemo(
    () => data?.pages[0]?.users ?? [],
    [data?.pages],
  );
  const allItems = useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data?.pages],
  );
  const total = data?.pages[0]?.total ?? 0;

  const visitCounts = useMemo(() => {
    const counts: Record<number, number> = {};
    for (const u of users) counts[u.id] = 0;
    for (const item of allItems) {
      for (const u of users) {
        if (item.visits[String(u.id)]) counts[u.id]++;
      }
    }
    return counts;
  }, [users, allItems]);

  if (!data || data.pages.length === 0) return null;

  if (allItems.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        <MapPin className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p className="text-lg font-medium">No trigpoints found</p>
        <p className="text-sm mt-1">
          Try adjusting your location, radius or filter settings.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto -mx-4 sm:mx-0">
      <table className="w-full text-sm">
        <thead className="sticky top-0 z-10 bg-gray-50 dark:bg-gray-800/95 backdrop-blur-sm">
          <tr className="border-b-2 border-gray-200 dark:border-gray-700">
            <th className="sticky left-0 z-20 bg-gray-50 dark:bg-gray-800/95 backdrop-blur-sm text-left px-3 py-2.5 font-semibold text-gray-700 dark:text-gray-300 min-w-[240px]">
              <div className="flex items-center justify-between">
                <span>Trigpoint</span>
                <span className="text-xs font-normal text-gray-500 dark:text-gray-400">
                  {allItems.length}
                  {total > allItems.length && ` of ${total}`}
                </span>
              </div>
            </th>
            {users.map((user) => (
              <th
                key={user.id}
                className="px-1 pt-3 pb-2 text-center font-semibold text-gray-700 dark:text-gray-300"
              >
                <div className="flex flex-col items-center gap-1.5">
                  <Link
                    to={`/profile/${user.id}`}
                    className="hover:text-trig-green-600 dark:hover:text-trig-green-400 transition-colors"
                  >
                    <span className="[writing-mode:vertical-rl] rotate-180 text-xs whitespace-nowrap inline-block">
                      {user.name}
                    </span>
                  </Link>
                  <span className="text-[10px] font-normal text-gray-400 dark:text-gray-500">
                    {visitCounts[user.id]}/{allItems.length}
                  </span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {allItems.map((item) => {
            const condInfo = getConditionInfo(item.condition);
            const bearing =
              item.wgs_lat && item.wgs_long
                ? calculateBearing(
                    centerLat,
                    centerLon,
                    item.wgs_lat,
                    item.wgs_long,
                  )
                : null;
            const allUnvisited = users.every(
              (u) => !item.visits[String(u.id)],
            );

            return (
              <tr
                key={item.id}
                className={`border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
                  allUnvisited
                    ? "bg-amber-50/50 dark:bg-amber-900/10"
                    : ""
                }`}
              >
                <td className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-2">
                  <div className="flex items-start gap-2">
                    {showListActions && (
                      <div className="flex-shrink-0 mt-0.5">
                        <AddToListButton trigId={item.id} />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <img
                          src={`/icons/conditions/${condInfo.icon}`}
                          alt={condInfo.label}
                          title={`Condition: ${condInfo.label}`}
                          className="w-4 h-4 flex-shrink-0"
                          width={16}
                          height={16}
                        />
                        <Link
                          to={`/trigs/${item.id}`}
                          className="font-medium text-gray-900 dark:text-gray-100 hover:text-trig-green-600 dark:hover:text-trig-green-400 truncate"
                        >
                          {item.name}
                        </Link>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                        {item.type_name && (
                          <span className="truncate">{item.type_name}</span>
                        )}
                        {item.distance_km != null && (
                          <>
                            <span className="text-gray-300 dark:text-gray-600">
                              &middot;
                            </span>
                            <span className="flex items-center gap-1 flex-shrink-0">
                              {bearing !== null && (
                                <BearingArrow bearing={bearing} />
                              )}
                              {formatDistance(item.distance_km, distanceUnit)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </td>
                {users.map((user) => {
                  const visit = item.visits[String(user.id)];
                  if (visit) {
                    const visitCondInfo = getConditionInfo(visit.condition);
                    return (
                      <td
                        key={user.id}
                        className="px-2 py-2 text-center"
                        title={`${visitCondInfo.label}${visit.date ? ` (${visit.date})` : ""}`}
                      >
                        <img
                          src={`/icons/conditions/${visitCondInfo.icon}`}
                          alt={visitCondInfo.label}
                          className="w-5 h-5 mx-auto"
                          width={20}
                          height={20}
                        />
                      </td>
                    );
                  }
                  return (
                    <td
                      key={user.id}
                      className="px-2 py-2 text-center"
                    >
                      <div className="w-5 h-5 mx-auto rounded-full bg-gray-100 dark:bg-gray-800" />
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} className="h-4" />
      {isFetchingNextPage && (
        <div className="flex justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        </div>
      )}
    </div>
  );
}

export default function Coop() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth0();
  const { data: userProfile } = useUserProfile("me");
  const { getConditionInfo } = useConditionInfo();

  // URL state
  const urlLat = searchParams.get("lat");
  const urlLon = searchParams.get("lon");
  const urlLocation = searchParams.get("location");
  const urlMaxKm = searchParams.get("maxKm");
  const urlUsers = searchParams.get("users");
  const urlMode = searchParams.get("mode") as CoopFilterMode | null;
  const urlCategories = searchParams.get("categories");

  // Local state
  const [selectedUsers, setSelectedUsers] = useState<SelectedUser[]>([]);
  const [centerLat, setCenterLat] = useState<number | undefined>(
    urlLat ? parseFloat(urlLat) : DEFAULT_LAT,
  );
  const [centerLon, setCenterLon] = useState<number | undefined>(
    urlLon ? parseFloat(urlLon) : DEFAULT_LON,
  );
  const [locationName, setLocationName] = useState(
    urlLocation || DEFAULT_LOCATION_NAME,
  );
  const [maxKm, setMaxKm] = useState<number | null>(
    urlMaxKm ? parseInt(urlMaxKm, 10) : DEFAULT_MAX_KM,
  );
  const [filterMode, setFilterMode] = useState<CoopFilterMode>(
    urlMode && urlMode in FILTER_MODE_LABELS ? urlMode : "all",
  );
  const [selectedStatuses, setSelectedStatuses] = useState<number[]>(() => {
    if (urlCategories) {
      const codes = urlCategories.split(",").map((c) => c.trim().toUpperCase());
      return ALL_STATUSES.filter(
        (id) => codes.includes(STATUS_ID_TO_CATEGORY_CODE[id]),
      );
    }
    return ALL_STATUSES;
  });

  const categories = useMemo(() => {
    if (selectedStatuses.length === ALL_STATUSES.length) return undefined;
    if (selectedStatuses.length === 0) return [];
    return selectedStatuses
      .map((id) => STATUS_ID_TO_CATEGORY_CODE[id])
      .filter(Boolean);
  }, [selectedStatuses]);

  // Apply user's default_categories preference (one-time, URL wins)
  const categoriesInitializedRef = useRef(!!urlCategories);
  useEffect(() => {
    if (categoriesInitializedRef.current || !userProfile) return;
    categoriesInitializedRef.current = true;

    const defaultCategories = userProfile.prefs?.ui_prefs?.default_categories;
    if (defaultCategories && defaultCategories.length > 0) {
      const statuses = defaultCategories
        .map((code: string) =>
          ALL_STATUSES.find((id) => STATUS_ID_TO_CATEGORY_CODE[id] === code),
        )
        .filter((id): id is number => id !== undefined);
      if (statuses.length > 0) {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization from async user profile
        setSelectedStatuses(statuses);
      }
    }
  }, [userProfile]);

  // Initialise current user as first selected user once profile loads
  const initialised = useRef(false);
  useEffect(() => {
    if (!userProfile || initialised.current) return;
    initialised.current = true;

    if (urlUsers) {
      // We'll populate from URL -- but we need to set user IDs first and
      // let the API resolve names. For now just add the current user and
      // any URL user IDs.
      const urlUserIds = urlUsers
        .split(",")
        .map((s) => parseInt(s.trim(), 10))
        .filter((n) => !isNaN(n));

      // Ensure current user is first
      const ids = [userProfile.id, ...urlUserIds.filter((id) => id !== userProfile.id)];
      // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization from URL params on profile load
      setSelectedUsers(
        ids.map((id) => ({
          id,
          name: id === userProfile.id ? userProfile.name : `User #${id}`,
        })),
      );
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization on profile load
      setSelectedUsers([{ id: userProfile.id, name: userProfile.name }]);
    }
  }, [userProfile, urlUsers]);

  // Sync URL state
  useEffect(() => {
    const params = new URLSearchParams();
    if (centerLat !== undefined && centerLat !== DEFAULT_LAT) {
      params.set("lat", centerLat.toString());
    }
    if (centerLon !== undefined && centerLon !== DEFAULT_LON) {
      params.set("lon", centerLon.toString());
    }
    if (locationName && locationName !== DEFAULT_LOCATION_NAME) {
      params.set("location", locationName);
    }
    if (maxKm !== null && maxKm !== DEFAULT_MAX_KM) {
      params.set("maxKm", maxKm.toString());
    }
    if (filterMode !== "all") {
      params.set("mode", filterMode);
    }
    if (categories && categories.length > 0) {
      params.set("categories", categories.join(","));
    }
    // Only store other user IDs (current user is always auto-included)
    const otherUsers = selectedUsers.filter(
      (u) => u.id !== userProfile?.id,
    );
    if (otherUsers.length > 0) {
      params.set("users", otherUsers.map((u) => u.id).join(","));
    }

    const newSearch = params.toString();
    const currentSearch = searchParams.toString();
    if (newSearch !== currentSearch) {
      setSearchParams(params, { replace: true });
    }
  }, [
    centerLat,
    centerLon,
    locationName,
    maxKm,
    filterMode,
    categories,
    selectedUsers,
    userProfile?.id,
    setSearchParams,
    searchParams,
  ]);

  const handleSelectLocation = useCallback(
    (lat: number, lon: number, name: string) => {
      setCenterLat(lat);
      setCenterLon(lon);
      setLocationName(name);
    },
    [],
  );

  const handleAddUser = useCallback(
    (user: SelectedUser) => {
      setSelectedUsers((prev) => {
        if (prev.length >= MAX_USERS) return prev;
        if (prev.some((u) => u.id === user.id)) return prev;
        return [...prev, user];
      });
    },
    [],
  );

  const handleRemoveUser = useCallback(
    (userId: number) => {
      setSelectedUsers((prev) => prev.filter((u) => u.id !== userId));
    },
    [],
  );

  const handleToggleStatus = useCallback((statusId: number) => {
    setSelectedStatuses((prev) =>
      prev.includes(statusId)
        ? prev.filter((s) => s !== statusId)
        : [...prev, statusId].sort((a, b) => a - b),
    );
  }, []);

  // Derive user IDs for the query
  const userIds = useMemo(
    () => selectedUsers.map((u) => u.id),
    [selectedUsers],
  );

  const distanceUnit =
    (userProfile?.prefs?.distance_ind as "K" | "M") || "K";

  const userRoles =
    (userProfile?.roles as string[]) || [];
  const showListActions =
    userRoles.includes("api-admin") && isAuthenticated;

  // Fetch co-op data
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useCoopData({
    userIds,
    lat: centerLat,
    lon: centerLon,
    maxKm: maxKm ?? undefined,
    categories,
    filterMode,
  });

  // Update user names once the API returns them (handles URL-loaded users)
  useEffect(() => {
    if (!data?.pages[0]?.users) return;
    const apiUsers = data.pages[0].users;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time name resolution for URL-loaded user IDs
    setSelectedUsers((prev) =>
      prev.map((u) => {
        const apiUser = apiUsers.find((au) => au.id === u.id);
        if (apiUser && u.name !== apiUser.name) {
          return { ...u, name: apiUser.name };
        }
        return u;
      }),
    );
  }, [data?.pages]);

  if (authLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        <title>Co-op Trigpointing | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="p-8 text-center">
              <Users className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Co-op Trigpointing
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Please log in to use the co-op trigpointing feature.
              </p>
            </div>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <title>Co-op Trigpointing | TrigpointingUK</title>
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link
            to="/experiment"
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-lg">
              <FlaskConical className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                Co-op Trigpointing
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Compare visits across members
              </p>
            </div>
          </div>
        </div>

        {/* Panel 1: User Selection */}
        <Card>
          <div className="p-4">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Members
            </h2>
            <UserSearchPanel
              selectedUsers={selectedUsers}
              onAddUser={handleAddUser}
              onRemoveUser={handleRemoveUser}
              currentUserId={userProfile?.id}
            />
          </div>
        </Card>

        {/* Panel 2: Location & Filters */}
        <Card>
          <div className="p-4">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Location &amp; Filters
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* Location search */}
              <div className="sm:col-span-2 lg:col-span-1">
                <LocationSearch
                  onSelectLocation={handleSelectLocation}
                  defaultLocation={
                    centerLat !== undefined && centerLon !== undefined
                      ? { lat: centerLat, lon: centerLon, name: locationName }
                      : undefined
                  }
                  excludeTypes={["user"]}
                />
              </div>

              {/* Radius */}
              <div className="sm:col-span-2 lg:col-span-1">
                <DistanceFilter
                  value={maxKm}
                  onChange={setMaxKm}
                  disabled={centerLat === undefined || centerLon === undefined}
                />
              </div>

              {/* Filter mode */}
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Show
                </label>
                <div className="relative">
                  <select
                    value={filterMode}
                    onChange={(e) =>
                      setFilterMode(e.target.value as CoopFilterMode)
                    }
                    className="w-full appearance-none px-3 py-2 pr-8 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-trig-green-500 focus:border-transparent text-sm"
                  >
                    {(
                      Object.entries(FILTER_MODE_LABELS) as [
                        CoopFilterMode,
                        string,
                      ][]
                    ).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Category filter icons */}
            <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Trigpoint types
              </label>
              <StatusFilter
                selectedStatuses={selectedStatuses}
                onToggleStatus={handleToggleStatus}
              />
            </div>
          </div>
        </Card>

        {/* Panel 3: Results Grid */}
        <Card>
          <div className="p-4">
            {selectedUsers.length <= 1 && !isLoading ? (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-40" />
                <p className="text-lg font-medium">
                  Add members to compare
                </p>
                <p className="text-sm mt-1">
                  Search for other members above to see which trigs they&rsquo;ve
                  visited compared to yours.
                </p>
              </div>
            ) : isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400 mr-2" />
                <span className="text-gray-500 dark:text-gray-400">
                  Loading comparison...
                </span>
              </div>
            ) : (
              <CoopGrid
                data={data}
                centerLat={centerLat ?? DEFAULT_LAT}
                centerLon={centerLon ?? DEFAULT_LON}
                distanceUnit={distanceUnit}
                showListActions={showListActions}
                getConditionInfo={getConditionInfo}
                hasNextPage={hasNextPage}
                isFetchingNextPage={isFetchingNextPage}
                fetchNextPage={fetchNextPage}
              />
            )}
          </div>
        </Card>
      </div>
    </>
  );
}
