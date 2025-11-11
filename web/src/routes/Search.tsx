import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import Header from "../components/layout/Header";
import {
  useUnifiedSearch,
  useCategorySearch,
  LocationSearchResult,
  LogSearchResult,
} from "../hooks/useSearchResults";
import { SearchTile } from "../components/search/SearchTile";
import { TileSettings, TileVisibility } from "../components/search/TileSettings";
import { TrigpointResultItem } from "../components/search/results/TrigpointResultItem";
import { StationNumberResultItem } from "../components/search/results/StationNumberResultItem";
import { PlaceResultItem } from "../components/search/results/PlaceResultItem";
import { UserResultItem } from "../components/search/results/UserResultItem";
import { PostcodeResultItem } from "../components/search/results/PostcodeResultItem";
import { CoordinateResultItem } from "../components/search/results/CoordinateResultItem";
import { LogResultItem } from "../components/search/results/LogResultItem";

const STORAGE_KEY = "search-tile-visibility";
const STORAGE_KEY_SHOW_EMPTY = "search-show-empty-tiles";

function loadTileVisibility(): TileVisibility {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      // Fall through to default
    }
  }
  return {
    trigpoints: true,
    station_numbers: true,
    places: true,
    users: true,
    postcodes: true,
    coordinates: true,
    log_substring: true,
    log_regex: true,
  };
}

function loadShowEmptyTiles(): boolean {
  const stored = localStorage.getItem(STORAGE_KEY_SHOW_EMPTY);
  return stored === "true";
}

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const [searchQuery, setSearchQuery] = useState(query);
  const [tileVisibility, setTileVisibility] = useState<TileVisibility>(
    loadTileVisibility()
  );
  const [showEmptyTiles, setShowEmptyTiles] = useState(loadShowEmptyTiles());
  const [collapsedTiles, setCollapsedTiles] = useState<Set<string>>(new Set());

  // Fetch unified search results
  const { data: unifiedResults, isLoading: isLoadingUnified } =
    useUnifiedSearch(query);

  // Infinite scroll queries for each category
  const {
    data: trigpointsPages,
    fetchNextPage: fetchNextTrigpoints,
    isFetchingNextPage: isFetchingMoreTrigpoints,
  } = useCategorySearch<LocationSearchResult>(
    "trigpoints",
    query,
    tileVisibility.trigpoints
  );

  const {
    data: stationNumbersPages,
    fetchNextPage: fetchNextStationNumbers,
    isFetchingNextPage: isFetchingMoreStationNumbers,
  } = useCategorySearch<LocationSearchResult>(
    "station-numbers",
    query,
    tileVisibility.station_numbers
  );

  const {
    data: placesPages,
    fetchNextPage: fetchNextPlaces,
    isFetchingNextPage: isFetchingMorePlaces,
  } = useCategorySearch<LocationSearchResult>(
    "places",
    query,
    tileVisibility.places
  );

  const {
    data: usersPages,
    fetchNextPage: fetchNextUsers,
    isFetchingNextPage: isFetchingMoreUsers,
  } = useCategorySearch<LocationSearchResult>(
    "users",
    query,
    tileVisibility.users
  );

  const {
    data: postcodesPages,
    fetchNextPage: fetchNextPostcodes,
    isFetchingNextPage: isFetchingMorePostcodes,
  } = useCategorySearch<LocationSearchResult>(
    "postcodes",
    query,
    tileVisibility.postcodes
  );

  const {
    data: logSubstringPages,
    fetchNextPage: fetchNextLogSubstring,
    isFetchingNextPage: isFetchingMoreLogSubstring,
  } = useCategorySearch<LogSearchResult>(
    "logs/substring",
    query,
    tileVisibility.log_substring
  );

  const {
    data: logRegexPages,
    fetchNextPage: fetchNextLogRegex,
    isFetchingNextPage: isFetchingMoreLogRegex,
  } = useCategorySearch<LogSearchResult>(
    "logs/regex",
    query,
    tileVisibility.log_regex
  );

  // Sync search input with URL
  useEffect(() => {
    setSearchQuery(query);
  }, [query]);

  // Save preferences to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tileVisibility));
  }, [tileVisibility]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_SHOW_EMPTY, showEmptyTiles.toString());
  }, [showEmptyTiles]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setSearchParams({ q: searchQuery.trim() });
    }
  };

  const toggleTileCollapse = (tileKey: string) => {
    setCollapsedTiles((prev) => {
      const next = new Set(prev);
      if (next.has(tileKey)) {
        next.delete(tileKey);
      } else {
        next.add(tileKey);
      }
      return next;
    });
  };

  const hideTile = (tileKey: keyof TileVisibility) => {
    setTileVisibility((prev) => ({
      ...prev,
      [tileKey]: false,
    }));
  };

  // Flatten paginated results
  const flattenPages = <T,>(pages: { pages?: Array<{ items: T[] }> } | undefined) => {
    if (!pages?.pages) return [];
    return pages.pages.flatMap((page) => page.items) as T[];
  };

  const trigpointItems = flattenPages<LocationSearchResult>(trigpointsPages);
  const stationNumberItems = flattenPages<LocationSearchResult>(stationNumbersPages);
  const placeItems = flattenPages<LocationSearchResult>(placesPages);
  const userItems = flattenPages<LocationSearchResult>(usersPages);
  const postcodeItems = flattenPages<LocationSearchResult>(postcodesPages);
  const logSubstringItems = flattenPages<LogSearchResult>(logSubstringPages);
  const logRegexItems = flattenPages<LogSearchResult>(logRegexPages);

  // Coordinate items come from unified results (no pagination needed)
  const coordinateItems = unifiedResults?.coordinates.items || [];

  // Get total and hasMore from paginated queries (more accurate than unified)
  const getTileDataFromPages = (
    pages:
      | {
          pages?: Array<{ total: number; has_more: boolean; items: unknown[] }>;
        }
      | undefined
  ) => {
    if (!pages?.pages || pages.pages.length === 0) {
      return { total: 0, has_more: false };
    }
    const firstPage = pages.pages[0];
    return {
      total: firstPage.total || 0,
      has_more: firstPage.has_more || false,
    };
  };

  const trigpointsData = getTileDataFromPages(trigpointsPages);
  const stationNumbersData = getTileDataFromPages(stationNumbersPages);
  const placesData = getTileDataFromPages(placesPages);
  const usersData = getTileDataFromPages(usersPages);
  const postcodesData = getTileDataFromPages(postcodesPages);
  const logSubstringData = getTileDataFromPages(logSubstringPages);
  const logRegexData = getTileDataFromPages(logRegexPages);

  // Coordinates use unified results (no pagination)
  const coordinatesData = {
    total: unifiedResults?.coordinates.total || 0,
    has_more: unifiedResults?.coordinates.has_more || false,
  };

  const shouldShowTile = (
    tileKey: keyof TileVisibility,
    totalResults: number
  ): boolean => {
    if (!tileVisibility[tileKey]) return false;
    if (totalResults > 0) return true;
    return showEmptyTiles;
  };

  if (!query || query.length < 2) {
    return (
      <>
        <Header />
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">Search</h1>
            <p className="text-gray-600 mb-6">
              Enter at least 2 characters to search across trigpoints, places,
              users, logs, and more.
            </p>
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search trigs, places, users, logs..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                autoFocus
              />
              <button
                type="submit"
                className="px-6 py-2 bg-trig-green-600 text-white rounded-md hover:bg-trig-green-700 transition-colors"
              >
                Search
              </button>
            </form>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Header />
      <div className="container mx-auto px-4 py-6">
        {/* Search Header */}
        <div className="mb-6">
          <form onSubmit={handleSearch} className="flex gap-2 mb-4">
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search trigs, places, users, logs..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-trig-green-500"
            />
            <button
              type="submit"
              className="px-6 py-2 bg-trig-green-600 text-white rounded-md hover:bg-trig-green-700 transition-colors"
            >
              Search
            </button>
          </form>

          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              Search Results for "{query}"
            </h1>
            <TileSettings
              visibility={tileVisibility}
              onChange={setTileVisibility}
              showEmptyTiles={showEmptyTiles}
              onToggleShowEmpty={() => setShowEmptyTiles(!showEmptyTiles)}
            />
          </div>
        </div>

        {/* Tiles Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Trigpoints Tile */}
          {shouldShowTile("trigpoints", trigpointsData.total) && (
            <SearchTile
              title="Trigpoints"
              icon="📍"
              totalResults={trigpointsData.total}
              items={trigpointItems}
              isLoading={isLoadingUnified}
              isFetchingMore={isFetchingMoreTrigpoints}
              hasMore={trigpointsData.has_more}
              onLoadMore={fetchNextTrigpoints}
              renderItem={(item) => <TrigpointResultItem item={item} />}
              categoryKey="trigpoints"
              isCollapsed={collapsedTiles.has("trigpoints")}
              onToggleCollapse={() => toggleTileCollapse("trigpoints")}
              onHide={() => hideTile("trigpoints")}
            />
          )}

          {/* Station Numbers Tile */}
          {shouldShowTile("station_numbers", stationNumbersData.total) && (
            <SearchTile
              title="Station Numbers"
              icon="🔢"
              totalResults={stationNumbersData.total}
              items={stationNumberItems}
              isLoading={isLoadingUnified}
              isFetchingMore={isFetchingMoreStationNumbers}
              hasMore={stationNumbersData.has_more}
              onLoadMore={fetchNextStationNumbers}
              renderItem={(item) => <StationNumberResultItem item={item} />}
              categoryKey="station_numbers"
              isCollapsed={collapsedTiles.has("station_numbers")}
              onToggleCollapse={() => toggleTileCollapse("station_numbers")}
              onHide={() => hideTile("station_numbers")}
            />
          )}

          {/* Places Tile */}
          {shouldShowTile("places", placesData.total) && (
            <SearchTile
              title="Places"
              icon="🏘️"
              totalResults={placesData.total}
              items={placeItems}
              isLoading={isLoadingUnified}
              isFetchingMore={isFetchingMorePlaces}
              hasMore={placesData.has_more}
              onLoadMore={fetchNextPlaces}
              renderItem={(item) => <PlaceResultItem item={item} />}
              categoryKey="places"
              isCollapsed={collapsedTiles.has("places")}
              onToggleCollapse={() => toggleTileCollapse("places")}
              onHide={() => hideTile("places")}
            />
          )}

          {/* Users Tile */}
          {shouldShowTile("users", usersData.total) && (
            <SearchTile
              title="Users"
              icon="👤"
              totalResults={usersData.total}
              items={userItems}
              isLoading={isLoadingUnified}
              isFetchingMore={isFetchingMoreUsers}
              hasMore={usersData.has_more}
              onLoadMore={fetchNextUsers}
              renderItem={(item) => <UserResultItem item={item} />}
              categoryKey="users"
              isCollapsed={collapsedTiles.has("users")}
              onToggleCollapse={() => toggleTileCollapse("users")}
              onHide={() => hideTile("users")}
            />
          )}

          {/* Postcodes Tile */}
          {shouldShowTile("postcodes", postcodesData.total) && (
            <SearchTile
              title="Postcodes"
              icon="📮"
              totalResults={postcodesData.total}
              items={postcodeItems}
              isLoading={isLoadingUnified}
              isFetchingMore={isFetchingMorePostcodes}
              hasMore={postcodesData.has_more}
              onLoadMore={fetchNextPostcodes}
              renderItem={(item) => <PostcodeResultItem item={item} />}
              categoryKey="postcodes"
              isCollapsed={collapsedTiles.has("postcodes")}
              onToggleCollapse={() => toggleTileCollapse("postcodes")}
              onHide={() => hideTile("postcodes")}
            />
          )}

          {/* Coordinates Tile */}
          {shouldShowTile("coordinates", coordinatesData.total) && (
            <SearchTile
              title="Coordinates"
              icon="🌐"
              totalResults={coordinatesData.total}
              items={coordinateItems}
              isLoading={isLoadingUnified}
              hasMore={false}
              onLoadMore={() => {}}
              renderItem={(item) => <CoordinateResultItem item={item} />}
              categoryKey="coordinates"
              isCollapsed={collapsedTiles.has("coordinates")}
              onToggleCollapse={() => toggleTileCollapse("coordinates")}
              onHide={() => hideTile("coordinates")}
            />
          )}

          {/* Log Substring Tile */}
          {shouldShowTile("log_substring", logSubstringData.total) && (
            <SearchTile
              title="Log Text"
              icon="📝"
              totalResults={logSubstringData.total}
              items={logSubstringItems}
              isLoading={isLoadingUnified}
              isFetchingMore={isFetchingMoreLogSubstring}
              hasMore={logSubstringData.has_more}
              onLoadMore={fetchNextLogSubstring}
              renderItem={(item) => <LogResultItem item={item} />}
              categoryKey="log_substring"
              isCollapsed={collapsedTiles.has("log_substring")}
              onToggleCollapse={() => toggleTileCollapse("log_substring")}
              onHide={() => hideTile("log_substring")}
              useCardLayout={true}
            />
          )}

          {/* Log Regex Tile */}
          {shouldShowTile("log_regex", logRegexData.total) && (
            <SearchTile
              title="Log Regex"
              icon="🔍"
              totalResults={logRegexData.total}
              items={logRegexItems}
              isLoading={isLoadingUnified}
              isFetchingMore={isFetchingMoreLogRegex}
              hasMore={logRegexData.has_more}
              onLoadMore={fetchNextLogRegex}
              renderItem={(item) => <LogResultItem item={item} />}
              categoryKey="log_regex"
              isCollapsed={collapsedTiles.has("log_regex")}
              onToggleCollapse={() => toggleTileCollapse("log_regex")}
              onHide={() => hideTile("log_regex")}
              useCardLayout={true}
            />
          )}
        </div>

        {/* No Results Message */}
        {!isLoadingUnified &&
          trigpointsData.total === 0 &&
          stationNumbersData.total === 0 &&
          placesData.total === 0 &&
          usersData.total === 0 &&
          postcodesData.total === 0 &&
          coordinatesData.total === 0 &&
          logSubstringData.total === 0 &&
          logRegexData.total === 0 && (
            <div className="text-center py-12">
              <p className="text-xl text-gray-600">
                No results found for "{query}"
              </p>
              <p className="text-gray-500 mt-2">
                Try a different search term or adjust your filters
              </p>
            </div>
          )}
      </div>
    </>
  );
}

