/**
 * Build the query parameters the trig list, map-points and download endpoints
 * share, so all three always agree about what the current filters mean.
 */

// Status ID to category code mapping
export const STATUS_ID_TO_CATEGORY_CODE: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

export interface TrigFilterOptions {
  lat?: number;
  lon?: number;
  maxKm?: number;
  statusIds?: number[]; // Status IDs to filter by (10, 20, 30, etc.)
  types?: string[]; // Type codes to filter by (e.g., ['HOTINE', 'FBM'])
  historicUse?: string[]; // Historic use values to filter by
  currentUse?: string[]; // Current use values to filter by
  conditions?: string[]; // Trig condition codes to filter by (e.g., ['G', 'R'])
  showLogged?: boolean; // Show trigpoints logged by the log user (default: true)
  showNotLogged?: boolean; // Show trigpoints not logged by the log user (default: true)
  loggedConditions?: string[]; // Show trigs logged with these conditions (e.g., ['G', 'R'])
  loggedBy?: number; // Whose logs the log filters refer to (default: the signed-in user)
  areaId?: number; // Filter to trigpoints within a specific area (single)
  areaIds?: number[]; // Filter to trigpoints within any of the specified areas (multi)
}

/**
 * True when a filter has been set to an empty selection, meaning "match
 * nothing" - the API has no way to express that, so callers short-circuit.
 * (An empty areaIds means "no area filter", not "no areas".)
 */
export function selectsNothing(options: TrigFilterOptions): boolean {
  const { types, historicUse, currentUse, conditions } = options;
  return [types, historicUse, currentUse, conditions].some(
    (values) => values !== undefined && values.length === 0,
  );
}

export function buildTrigFilterParams(options: TrigFilterOptions): URLSearchParams {
  const {
    lat,
    lon,
    maxKm,
    statusIds,
    types,
    historicUse,
    currentUse,
    conditions,
    showLogged = true,
    showNotLogged = true,
    loggedConditions,
    loggedBy,
    areaId,
    areaIds,
  } = options;
  const params = new URLSearchParams();

  if (lat !== undefined && lon !== undefined) {
    params.append("lat", lat.toString());
    params.append("lon", lon.toString());
    if (maxKm !== undefined) {
      params.append("max_km", maxKm.toString());
    }
  }

  if (statusIds && statusIds.length > 0) {
    // Convert status IDs to category codes for the API
    const categoryCodes = statusIds
      .map((id) => STATUS_ID_TO_CATEGORY_CODE[id])
      .filter((code): code is string => code !== undefined);
    if (categoryCodes.length > 0) {
      params.append("categories", categoryCodes.join(","));
    }
  }

  if (types && types.length > 0) {
    params.append("types", types.join(","));
  }
  if (historicUse && historicUse.length > 0) {
    params.append("historic_use", historicUse.join(","));
  }
  if (currentUse && currentUse.length > 0) {
    params.append("current_use", currentUse.join(","));
  }
  if (conditions && conditions.length > 0) {
    params.append("conditions", conditions.join(","));
  }

  if (loggedBy !== undefined) {
    params.append("logged_by", loggedBy.toString());
  }
  // Log filter: showLogged=false means exclude found, showNotLogged=false means only found
  if (!showLogged) {
    params.append("exclude_found", "true");
  }
  if (!showNotLogged) {
    params.append("only_found", "true");
  }
  // Logged conditions filter - show trigs logged with specific conditions
  if (loggedConditions && loggedConditions.length > 0) {
    params.append("logged_conditions", loggedConditions.join(","));
  }

  if (areaIds && areaIds.length > 0) {
    params.append("area_ids", areaIds.join(","));
  } else if (areaId !== undefined) {
    params.append("area_id", areaId.toString());
  }

  return params;
}
