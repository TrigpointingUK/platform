import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import DirectionArrow from "../ui/DirectionArrow";
import { Trig } from "../../lib/api";
import { useAreasContaining, type Area } from "../../hooks/useAreasContaining";
import { useUserProfile, type MapLinkOption } from "../../hooks/useUserProfile";
import { useConditionInfo } from "../../hooks/useConditionInfo";
import { generateMapUrl, getTrigpointingUKMapPath, isInternalMapLink, MAP_LINK_DEFAULTS } from "../../lib/mapLinks";
import { calculateDistance, calculateBearing } from "../../lib/coordinates";
import FacebookShareButton, { getCanonicalOrigin } from "../ui/FacebookShareButton";
import { Link2 } from "lucide-react";

interface TrigInfoSectionProps {
  trig: Trig;
  /** Show the nearby areas dropdown. Default: true */
  showNearbyDropdown?: boolean;
  /** Custom className for the Card wrapper */
  className?: string;
  /** Show admin OG preview link */
  isAdmin?: boolean;
}

export default function TrigInfoSection({ 
  trig, 
  showNearbyDropdown = true,
  className = "mb-6",
  isAdmin = false,
}: TrigInfoSectionProps) {
  const trigIdNum = trig.id;
  
  // Get current user's UI preferences for map links
  const { data: userProfile } = useUserProfile("me");
  const mapLinkGridref: MapLinkOption = userProfile?.prefs?.ui_prefs?.map_link_gridref ?? MAP_LINK_DEFAULTS.gridref;
  const mapLinkWgs: MapLinkOption = userProfile?.prefs?.ui_prefs?.map_link_wgs ?? MAP_LINK_DEFAULTS.wgs;
  const mapLinkThumbnail: MapLinkOption = userProfile?.prefs?.ui_prefs?.map_link_thumbnail ?? MAP_LINK_DEFAULTS.thumbnail;

  // Get condition info from API or fallback
  const { getConditionInfo } = useConditionInfo();

  // Fetch areas containing this trigpoint
  const { data: areasData, isLoading: isAreasLoading } = useAreasContaining(
    Number(trig.wgs_lat),
    Number(trig.wgs_long)
  );

  // Flatten areas for the dropdown
  const allAreas = useMemo(() => {
    if (!areasData?.groups) return [];
    const areas: Area[] = [];
    for (const group of areasData.groups) {
      areas.push(...group.areas);
    }
    // Sort by area type name, then area name
    return areas.sort((a, b) => {
      const typeCompare = a.area_type.name.localeCompare(b.area_type.name);
      if (typeCompare !== 0) return typeCompare;
      return a.name.localeCompare(b.name);
    });
  }, [areasData]);

  // State for areas dropdown
  const [isAreasDropdownOpen, setIsAreasDropdownOpen] = useState(false);

  const condition = getConditionInfo(trig.condition);
  const apiBase = import.meta.env.VITE_API_BASE as string;

  // Helper function to create wiki links
  const getWikiUrl = (value: string) => {
    const wikiValue = value.replace(/ /g, "_");
    return `https://wiki.trigpointing.uk/${wikiValue}`;
  };

  // Helper function to check if a value should have a wiki link
  const shouldHaveWikiLink = (value: string) => {
    return value && value.toLowerCase() !== "none" && value.trim() !== "";
  };

  return (
    <Card className={className}>
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left: Info Grid */}
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-trig-green-600 mb-4 flex items-center gap-2">
            <Link 
              to={`/trigs/${trigIdNum}`}
              className="hover:underline"
            >
              {trig.waypoint} - {trig.name}
            </Link>
            <FacebookShareButton url={`${getCanonicalOrigin()}/trigs/${trigIdNum}`} />
            {isAdmin && (
              <button
                onClick={() => {
                  const apiBase = import.meta.env.VITE_API_BASE as string;
                  window.open(`${apiBase}/v1/trigs/${trigIdNum}/opengraph-image?refresh=1`, "_blank", "noopener,noreferrer");
                }}
                title="Preview OG image"
                className="inline-flex items-center text-gray-400 hover:text-trig-green-600 dark:text-gray-500 dark:hover:text-trig-green-400 transition-colors"
              >
                <Link2 className="w-4 h-4" />
              </button>
            )}
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <span className="font-semibold text-gray-700 dark:text-gray-300">
                Grid reference{trig.grid_system === 'ie' ? ' (Irish)' : ''}:
              </span>{" "}
              {isInternalMapLink(mapLinkGridref) ? (
                <Link
                  to={getTrigpointingUKMapPath({
                    trigId: trigIdNum,
                    wgsLat: Number(trig.wgs_lat),
                    wgsLong: Number(trig.wgs_long),
                  })}
                  className="text-trig-green-600 hover:underline"
                >
                  {trig.osgb_gridref}
                </Link>
              ) : (
                <a
                  href={generateMapUrl(mapLinkGridref, {
                    trigId: trigIdNum,
                    wgsLat: Number(trig.wgs_lat),
                    wgsLong: Number(trig.wgs_long),
                    gridSystem: trig.grid_system as 'gb' | 'ie' | null,
                  }) || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-trig-green-600 hover:underline"
                >
                  {trig.osgb_gridref}
                </a>
              )}
            </div>

            <div>
              <span className="font-semibold text-gray-700 dark:text-gray-300">
                WGS coordinates:
              </span>{" "}
              {isInternalMapLink(mapLinkWgs) ? (
                <Link
                  to={getTrigpointingUKMapPath({
                    trigId: trigIdNum,
                    wgsLat: Number(trig.wgs_lat),
                    wgsLong: Number(trig.wgs_long),
                  })}
                  className="text-trig-green-600 hover:underline"
                >
                  {Number(trig.wgs_lat).toFixed(7)}, {Number(trig.wgs_long).toFixed(7)}
                </Link>
              ) : (
                <a
                  href={generateMapUrl(mapLinkWgs, {
                    trigId: trigIdNum,
                    wgsLat: Number(trig.wgs_lat),
                    wgsLong: Number(trig.wgs_long),
                    gridSystem: trig.grid_system as 'gb' | 'ie' | null,
                  }) || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-trig-green-600 hover:underline"
                >
                  {Number(trig.wgs_lat).toFixed(7)}, {Number(trig.wgs_long).toFixed(7)}
                </a>
              )}
            </div>

            {trig.details?.osgb_eastings != null && trig.details?.osgb_northings != null && (
              <div>
                <span className="font-semibold text-gray-700 dark:text-gray-300">
                  OSGB36:
                </span>{" "}
                {Number(trig.details.osgb_eastings).toFixed(3)}, {Number(trig.details.osgb_northings).toFixed(3)}
              </div>
            )}

            {trig.details?.osgb_height != null && (
              <div>
                <span className="font-semibold text-gray-700 dark:text-gray-300">
                  Height above sea level:
                </span>{" "}
                {Number(trig.details.osgb_height).toFixed(3)}m
              </div>
            )}

            {trig.details && trig.details.postcode && (
              <div>
                <span className="font-semibold text-gray-700 dark:text-gray-300">
                  Postcode:
                </span>{" "}
                <a
                  href={`https://www.google.co.uk/maps/search/${encodeURIComponent(trig.details.postcode)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-trig-green-600 hover:underline"
                >
                  {trig.details.postcode}
                </a>
              </div>
            )}

            <div>
              <span className="font-semibold text-gray-700 dark:text-gray-300">Type:</span>{" "}
              {(() => {
                // Determine display text: type_name if same as category, else "category · type"
                const displayText = trig.type_name
                  ? trig.type_code === trig.category_code
                    ? trig.type_name
                    : `${trig.category_name} · ${trig.type_name}`
                  : "Unknown";
                
                // Use type_wiki_url if available, otherwise fall back to name-based URL
                const wikiUrl = trig.type_wiki_url?.trim() 
                  ? trig.type_wiki_url 
                  : (trig.type_name ? getWikiUrl(trig.type_name) : null);
                
                return wikiUrl && trig.type_name && shouldHaveWikiLink(trig.type_name) ? (
                  <a
                    href={wikiUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-trig-green-600 hover:underline"
                  >
                    {displayText}
                  </a>
                ) : (
                  displayText
                );
              })()}
            </div>

            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-700 dark:text-gray-300">
                Condition:
              </span>
              <Badge variant={condition.variant}>
                <img
                  src={`/icons/conditions/${condition.icon}`}
                  alt=""
                  className="w-4 h-4 inline-block mr-1.5"
                />
                {condition.label}
              </Badge>
            </div>

            {trig.details && (
              <>
                {trig.details.fb_number && (
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">
                      Flush Bracket:
                    </span>{" "}
                    {trig.details.fb_number}
                  </div>
                )}

                {trig.details.stn_number_active && trig.details.stn_number_active.trim() !== "" && (
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">
                      Active Station:
                    </span>{" "}
                    {trig.details.stn_number_active}
                  </div>
                )}

                {trig.details.stn_number_passive && trig.details.stn_number_passive.trim() !== "" && (
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">
                      Passive Station:
                    </span>{" "}
                    <a
                      href={`https://www.ordnancesurvey.co.uk/geodesy-positioning/legacy-data/passive-search/passive-station/${trig.details.stn_number_passive}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-trig-green-600 hover:underline"
                    >
                      {trig.details.stn_number_passive}
                    </a>
                  </div>
                )}

                {trig.details.stn_number_osgb36 && trig.details.stn_number_osgb36.trim() !== "" && (
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">
                      OSGB36 Station:
                    </span>{" "}
                    {trig.details.stn_number_osgb36}
                  </div>
                )}

                <div>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">
                    Recent use:
                  </span>{" "}
                  {shouldHaveWikiLink(trig.details.current_use) ? (
                    <a
                      href={getWikiUrl(trig.details.current_use)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-trig-green-600 hover:underline"
                    >
                      {trig.details.current_use}
                    </a>
                  ) : (
                    trig.details.current_use
                  )}
                </div>

                <div>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">
                    Historic use:
                  </span>{" "}
                  {shouldHaveWikiLink(trig.details.historic_use) ? (
                    <a
                      href={getWikiUrl(trig.details.historic_use)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-trig-green-600 hover:underline"
                    >
                      {trig.details.historic_use}
                    </a>
                  ) : (
                    trig.details.historic_use
                  )}
                </div>

                <div>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">
                    County:
                  </span>{" "}
                  {trig.details.county}
                </div>

                <div>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">
                    Nearest town:
                  </span>{" "}
                  {trig.details.town}
                </div>
              </>
            )}
          </div>

          {/* Original OS Location - shown when condition is 'M' (Moved) */}
          {trig.condition === 'M' && trig.details?.original_osgb_gridref && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Original OS Location
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">
                    Grid reference{trig.details.original_grid_system === 'ie' ? ' (Irish)' : ''}:
                  </span>{" "}
                  {trig.details.original_wgs_lat != null && trig.details.original_wgs_long != null ? (
                    isInternalMapLink(mapLinkGridref) ? (
                      <Link
                        to={getTrigpointingUKMapPath({
                          trigId: trigIdNum,
                          wgsLat: Number(trig.details.original_wgs_lat),
                          wgsLong: Number(trig.details.original_wgs_long),
                        })}
                        className="text-trig-green-600 hover:underline"
                      >
                        {trig.details.original_osgb_gridref}
                      </Link>
                    ) : (
                      <a
                        href={generateMapUrl(mapLinkGridref, {
                          trigId: trigIdNum,
                          wgsLat: Number(trig.details.original_wgs_lat),
                          wgsLong: Number(trig.details.original_wgs_long),
                          gridSystem: trig.details.original_grid_system as 'gb' | 'ie' | null,
                        }) || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-trig-green-600 hover:underline"
                      >
                        {trig.details.original_osgb_gridref}
                      </a>
                    )
                  ) : (
                    trig.details.original_osgb_gridref
                  )}
                </div>
                {trig.details.original_wgs_lat != null && trig.details.original_wgs_long != null && (
                  <>
                    <div>
                      <span className="font-semibold text-gray-700 dark:text-gray-300">
                        WGS coordinates:
                      </span>{" "}
                      {isInternalMapLink(mapLinkWgs) ? (
                        <Link
                          to={getTrigpointingUKMapPath({
                            trigId: trigIdNum,
                            wgsLat: Number(trig.details.original_wgs_lat),
                            wgsLong: Number(trig.details.original_wgs_long),
                          })}
                          className="text-trig-green-600 hover:underline"
                        >
                          {Number(trig.details.original_wgs_lat).toFixed(7)}, {Number(trig.details.original_wgs_long).toFixed(7)}
                        </Link>
                      ) : (
                        <a
                          href={generateMapUrl(mapLinkWgs, {
                            trigId: trigIdNum,
                            wgsLat: Number(trig.details.original_wgs_lat),
                            wgsLong: Number(trig.details.original_wgs_long),
                            gridSystem: trig.details.original_grid_system as 'gb' | 'ie' | null,
                          }) || '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-trig-green-600 hover:underline"
                        >
                          {Number(trig.details.original_wgs_lat).toFixed(7)}, {Number(trig.details.original_wgs_long).toFixed(7)}
                        </a>
                      )}
                    </div>
                    <div className="md:col-span-2 flex items-center gap-2">
                      <span className="font-semibold text-gray-700 dark:text-gray-300">
                        Distance from original:
                      </span>{" "}
                      {(() => {
                        const distanceMetres = calculateDistance(
                          Number(trig.details.original_wgs_lat),
                          Number(trig.details.original_wgs_long),
                          Number(trig.wgs_lat),
                          Number(trig.wgs_long)
                        );
                        const bearing = calculateBearing(
                          Number(trig.details.original_wgs_lat),
                          Number(trig.details.original_wgs_long),
                          Number(trig.wgs_lat),
                          Number(trig.wgs_long)
                        );
                        return (
                          <>
                            <span>{distanceMetres < 1000 ? `${Math.round(distanceMetres)}m` : `${(distanceMetres / 1000).toFixed(2)}km`}</span>
                            <DirectionArrow bearing={bearing} size={14} />
                          </>
                        );
                      })()}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Map Links */}
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                <Link
                  to={`/map?lat=${trig.wgs_lat}&lon=${trig.wgs_long}&trig=${trigIdNum}`}
                  className="text-trig-green-600 hover:underline font-semibold"
                >
                  🗺️ View on Interactive Map
                </Link>
              </div>
              <div>
                <Link
                  to={`/trigs/${trigIdNum}/photos`}
                  className="text-trig-green-600 hover:underline font-semibold"
                >
                  📷 View Photo Album
                </Link>
              </div>
              {/* Nearby trigpoints dropdown */}
              {showNearbyDropdown && (
                <div className="relative">
                  <button
                    onClick={() => setIsAreasDropdownOpen(!isAreasDropdownOpen)}
                    className="text-trig-green-600 hover:underline font-semibold flex items-center gap-1"
                  >
                    📍 View Nearby Trigpoints
                    {isAreasLoading ? (
                      <span className="text-gray-400 text-xs">(loading...)</span>
                    ) : (
                      <svg
                        className={`w-4 h-4 transition-transform ${isAreasDropdownOpen ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    )}
                  </button>
                  
                  {isAreasDropdownOpen && (
                    <>
                      {/* Backdrop to close dropdown */}
                      <div
                        className="fixed inset-0 z-[1100]"
                        onClick={() => setIsAreasDropdownOpen(false)}
                      />
                      
                      {/* Dropdown menu */}
                      <div className="absolute left-0 mt-1 min-w-72 w-max max-w-[90vw] max-h-64 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg z-[1101]">
                        {/* All nearby option */}
                        <Link
                          to={`/trigs?lat=${trig.wgs_lat}&lon=${trig.wgs_long}&location=${encodeURIComponent(`${trig.waypoint} - ${trig.name}`)}`}
                          className="block px-3 py-2 text-sm text-gray-700 hover:bg-trig-green-50 hover:text-trig-green-700 font-medium"
                          onClick={() => setIsAreasDropdownOpen(false)}
                        >
                          All nearby trigpoints
                        </Link>
                        
                        {/* Divider and area options */}
                        {allAreas.length > 0 && (
                          <>
                            <div className="border-t border-gray-200 my-1" />
                            {allAreas.map((area) => (
                              <Link
                                key={area.id}
                                to={`/trigs?lat=${trig.wgs_lat}&lon=${trig.wgs_long}&location=${encodeURIComponent(`${trig.waypoint} - ${trig.name}`)}&areaId=${area.id}&areaName=${encodeURIComponent(`${area.area_type.name} : ${area.name}`)}`}
                                className="block px-3 py-2 text-sm text-gray-700 hover:bg-trig-green-50 hover:text-trig-green-700 border-b border-gray-100 last:border-b-0"
                                onClick={() => setIsAreasDropdownOpen(false)}
                              >
                                <span className="font-medium">{area.area_type.name}</span>
                                <span className="text-gray-400 mx-1">:</span>
                                <span>{area.name}</span>
                              </Link>
                            ))}
                          </>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Map Thumbnail */}
        <div className="flex-shrink-0">
          {isInternalMapLink(mapLinkThumbnail) ? (
            <Link
              to={getTrigpointingUKMapPath({
                trigId: trigIdNum,
                wgsLat: Number(trig.wgs_lat),
                wgsLong: Number(trig.wgs_long),
              })}
              title="View on map"
            >
              <img
                src={`${apiBase}/v1/trigs/${trigIdNum}/map`}
                alt={`Map thumbnail for ${trig.name}`}
                className="w-[110px] h-[110px] border border-gray-300 rounded hover:border-trig-green-500 hover:shadow-md transition-all cursor-pointer"
                width={110}
                height={110}
                fetchPriority="high"
              />
            </Link>
          ) : (
            <a
              href={generateMapUrl(mapLinkThumbnail, {
                trigId: trigIdNum,
                wgsLat: Number(trig.wgs_lat),
                wgsLong: Number(trig.wgs_long),
                gridSystem: trig.grid_system as 'gb' | 'ie' | null,
              }) || '#'}
              target="_blank"
              rel="noopener noreferrer"
              title="View on map"
            >
              <img
                src={`${apiBase}/v1/trigs/${trigIdNum}/map`}
                alt={`Map thumbnail for ${trig.name}`}
                className="w-[110px] h-[110px] border border-gray-300 rounded hover:border-trig-green-500 hover:shadow-md transition-all cursor-pointer"
                width={110}
                height={110}
                fetchPriority="high"
              />
            </a>
          )}
        </div>
      </div>
    </Card>
  );
}

