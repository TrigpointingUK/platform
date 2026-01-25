/**
 * API client utilities for making requests to the backend.
 *
 * For authenticated requests, there are two approaches:
 *
 * 1. **New approach (recommended)**: Use authenticatedFetch utilities with automatic 401 retry
 *    ```typescript
 *    import { authenticatedGet, authenticatedPost } from './authenticatedFetch';
 *    const data = await authenticatedGet('/v1/endpoint', getAccessTokenSilently);
 *    ```
 *
 * 2. **Legacy approach**: Pass a pre-fetched token
 *    ```typescript
 *    const token = await getAccessTokenSilently();
 *    const data = await apiGet('/v1/endpoint', token);
 *    ```
 *
 * The new approach handles 401 errors by automatically refreshing the token and retrying.
 */

// Re-export authenticated fetch utilities for convenience
export {
  authenticatedFetch,
  authenticatedGet,
  authenticatedPost,
  authenticatedPatch,
  authenticatedDelete,
  AuthenticationError,
  type GetAccessTokenSilently,
} from './authenticatedFetch';

const API_BASE = import.meta.env.VITE_API_BASE as string;

// Debug logging for API_BASE
if (!API_BASE) {
  console.error('CRITICAL: VITE_API_BASE is not defined!');
} else {
  console.log('API_BASE configured as:', API_BASE);
}

/**
 * Custom error for duplicate log attempts (409 Conflict)
 */
export class DuplicateLogError extends Error {
  existingLogId: number;
  constructor(message: string, existingLogId: number) {
    super(message);
    this.name = "DuplicateLogError";
    this.existingLogId = existingLogId;
  }
}

/**
 * Parse error response and throw appropriate error type
 */
function parseAndThrowError(status: number, text: string, statusText: string): never {
  // Check for 409 Conflict with duplicate log info
  if (status === 409) {
    try {
      const errorData = JSON.parse(text);
      if (errorData.detail?.existing_log_id) {
        throw new DuplicateLogError(
          errorData.detail.message || "Duplicate log exists",
          errorData.detail.existing_log_id
        );
      }
    } catch (e) {
      if (e instanceof DuplicateLogError) throw e;
      // Fall through to generic error
    }
  }
  throw new Error(`HTTP ${status}: ${text || statusText}`);
}

export async function apiGet<T>(url: string, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    // No credentials - using Bearer tokens only
  });
  
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  
  return res.json() as Promise<T>;
}

export async function apiPost<T>(
  url: string,
  data: unknown,
  token?: string
): Promise<T> {
  const fullUrl = `${API_BASE}${url}`;
  console.log('apiPost called:', { url, fullUrl, API_BASE, hasToken: !!token });
  
  const res = await fetch(fullUrl, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  });
  
  console.log('apiPost response:', { url, status: res.status, ok: res.ok });
  
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.error('apiPost error:', `HTTP ${res.status}: ${text || res.statusText}`);
    parseAndThrowError(res.status, text, res.statusText);
  }
  
  const jsonResponse = await res.json() as Promise<T>;
  console.log('apiPost success:', { url, response: jsonResponse });
  return jsonResponse;
}

export async function apiPatch<T>(
  url: string,
  data: unknown,
  token?: string
): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    parseAndThrowError(res.status, text, res.statusText);
  }
  
  return res.json() as Promise<T>;
}

export async function apiDelete<T>(
  url: string,
  token?: string
): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  
  return res.json() as Promise<T>;
}

export interface RotatePhotoRequest {
  angle: number;
}

export interface Photo {
  id: number;
  log_id: number;
  user_id: number;
  icon_url: string;
  photo_url: string;
  caption: string;
  type: string;
  filesize: number;
  height: number;
  width: number;
  icon_filesize: number;
  icon_height: number;
  icon_width: number;
  text_desc: string;
  license: string;
  user_name?: string;
  trig_id?: number;
  trig_name?: string;
  log_date?: string;
}

/**
 * Rotate a photo by a given angle (90, 180, or 270 degrees)
 */
export async function rotatePhoto(
  photoId: number,
  angle: number,
  token?: string
): Promise<Photo> {
  return apiPost<Photo>(`/v1/photos/${photoId}/rotate`, { angle }, token);
}

/**
 * Upload a photo for a log
 */
export async function uploadPhoto(
  logId: number,
  file: File,
  caption: string,
  text_desc: string,
  type: string,
  license: string,
  token: string
): Promise<Photo> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const formData = new FormData();
  formData.append("file", file);
  formData.append("caption", caption);
  formData.append("text_desc", text_desc);
  formData.append("type", type);
  formData.append("license", license);

  const response = await fetch(`${apiBase}/v1/photos?log_id=${logId}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  return response.json() as Promise<Photo>;
}

/**
 * Update photo metadata
 */
export async function updatePhoto(
  photoId: number,
  updates: {
    caption?: string;
    text_desc?: string;
    type?: string;
    license?: string;
  },
  token: string
): Promise<Photo> {
  return apiPatch<Photo>(`/v1/photos/${photoId}`, updates, token);
}

/**
 * Delete a photo (soft delete)
 */
export async function deletePhoto(
  photoId: number,
  token: string
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/photos/${photoId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
}

/**
 * Get photos for a log
 */
export async function getLogPhotos(logId: number): Promise<Photo[]> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/photos?log_id=${logId}`);
  
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
  
  const data = await response.json();
  return data.items || [];
}

export interface AttrSourceInfo {
  id: number;
  name: string;
  url?: string;
}

export interface AttrSetData {
  values: Record<number, string>;
}

export interface TrigAttrsData {
  source: AttrSourceInfo;
  attr_names: Record<number, string>;
  attribute_sets: AttrSetData[];
}

export interface TrigDetails {
  current_use: string;
  historic_use: string;
  wgs_height: number | null;
  osgb_eastings: number | null;
  osgb_northings: number | null;
  osgb_height: number | null;
  postcode: string;
  county: string;
  town: string;
  fb_number: string;
  stn_number: string;
  stn_number_active?: string;
  legal_message?: string | null;
  stn_number_passive?: string;
  stn_number_osgb36?: string;
}

export interface TrigStats {
  logged_first: string | null;
  logged_last: string | null;
  logged_count: number;
  found_last: string | null;
  found_count: number;
  photo_count: number;
  score_mean: string;
  score_baysian: string;
}

export interface Trig {
  id: number;
  waypoint: string;
  name: string;
  status_name?: string;
  condition: string;
  /** WGS84 latitude (serialized as float, rounded to 5dp) */
  wgs_lat: number;
  /** WGS84 longitude (serialized as float, rounded to 5dp) */
  wgs_long: number;
  osgb_gridref: string;
  /** Grid system: 'gb' (British National Grid) or 'ie' (Irish Grid) */
  grid_system?: 'gb' | 'ie';
  /** Country name (e.g., 'England', 'Ireland', 'Northern Ireland') */
  country_name?: string;
  /** Type code (e.g., HOTINE, FBM) */
  type_code?: string;
  /** Type display name (e.g., Hotine Pillar, Flush Bracket Mark) */
  type_name?: string;
  /** Wiki URL for this type (use for linking to wiki) */
  type_wiki_url?: string;
  /** Category code (e.g., PILLAR, FBM, SURVEY_MARK) */
  category_code?: string;
  /** Category display name (e.g., Pillar, FBM, Survey mark) */
  category_name?: string;
  details?: TrigDetails;
  stats?: TrigStats;
  attrs?: TrigAttrsData[];
}

export interface Log {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
  trig_lat?: number;
  trig_lon?: number;
  trig_condition?: string;
  date: string;
  time: string;
  osgb_eastings: number;
  osgb_northings: number;
  osgb_gridref: string;
  fb_number: string;
  condition: string;
  comment: string;
  score: number;
  source: string;
  // Status: 'P' = Published (default), 'D' = Draft
  status?: string;
  location_distance_m?: number;
  photos?: Photo[];
}

export interface LogCreateInput {
  date: string;
  time: string;
  osgb_eastings: number;
  osgb_northings: number;
  osgb_gridref: string;
  fb_number?: string;
  condition: string;
  comment?: string;
  score: number;
  source?: string;
}

export interface LogUpdateInput {
  date?: string;
  time?: string;
  osgb_eastings?: number;
  osgb_northings?: number;
  osgb_gridref?: string;
  fb_number?: string;
  condition?: string;
  comment?: string;
  score?: number;
  source?: string;
}

/**
 * Create a new log for a trigpoint
 */
export async function createLog(
  trigId: number,
  data: LogCreateInput,
  token: string
): Promise<Log> {
  return apiPost<Log>(`/v1/logs?trig_id=${trigId}`, data, token);
}

/**
 * Update an existing log
 */
export async function updateLog(
  logId: number,
  data: LogUpdateInput,
  token: string
): Promise<Log> {
  return apiPatch<Log>(`/v1/logs/${logId}`, data, token);
}

/**
 * Delete a log (hard delete - also soft-deletes associated photos)
 */
export async function deleteLog(
  logId: number,
  token: string
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/logs/${logId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
}

export interface LegacyLoginRequest {
  username: string;
  password: string;
  email: string;
}

export interface LegacyLoginResponse {
  id: number;
  name: string;
  email: string;
  email_valid: string;
  firstname: string;
  surname: string;
  homepage: string | null;
  about: string;
  member_since?: string;
}

/**
 * Legacy login endpoint - migrates user account to Auth0
 */
export async function legacyLogin(
  data: LegacyLoginRequest
): Promise<LegacyLoginResponse> {
  return apiPost<LegacyLoginResponse>(`/v1/legacy/login`, data);
}

export interface ContactRequest {
  name: string;
  email: string;
  subject: string;
  message: string;
  user_id?: number;
  auth0_user_id?: string;
  username?: string;
}

export interface ContactResponse {
  success: boolean;
  message: string;
}

/**
 * Submit contact form
 */
export async function submitContact(
  data: ContactRequest,
  token?: string
): Promise<ContactResponse> {
  return apiPost<ContactResponse>(`/v1/admin/contact`, data, token);
}

export interface AdminUserSearchResult {
  id: number;
  name: string;
  email: string;
  email_valid: string;
  auth0_user_id?: string | null;
  has_auth0_account: boolean;
}

export interface AdminUserSearchResponse {
  items: AdminUserSearchResult[];
}

export async function searchLegacyUsers(
  query: string,
  token: string
): Promise<AdminUserSearchResponse> {
  return apiGet<AdminUserSearchResponse>(
    `/v1/admin/legacy-migration/users?q=${encodeURIComponent(query)}&limit=250`,
    token
  );
}

export interface AdminMigrationRequest {
  user_id: number;
  email: string;
}

export interface AdminMigrationResponse {
  user_id: number;
  username: string;
  email: string;
  auth0_user_id: string;
  message: string;
}

export async function migrateLegacyUser(
  payload: AdminMigrationRequest,
  token: string
): Promise<AdminMigrationResponse> {
  return apiPost<AdminMigrationResponse>(
    `/v1/admin/legacy-migration/migrate`,
    payload,
    token
  );
}

// Admin Trigpoint Management Types and Functions

export interface TrigNeedsAttentionSummary {
  count: number;
  latest_update?: string;
}

export interface TrigNeedsAttentionListItem {
  id: number;
  waypoint: string;
  name: string;
  condition: string;
  needs_attention: number;
  attention_comment: string;
  upd_timestamp?: string;
}

export interface TrigNeedsAttentionListResponse {
  items: TrigNeedsAttentionListItem[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export interface TrigAdminDetail {
  id: number;
  waypoint: string;
  name: string;
  fb_number: string;
  stn_number: string;
  stn_number_active: string;
  stn_number_passive: string;
  stn_number_osgb36: string;
  status_id: number;
  type_id: number | null;
  current_use: string;
  historic_use: string;
  condition: string;
  /** WGS84 latitude (8dp precision, ~1mm) */
  wgs_lat: number;
  /** WGS84 longitude (8dp precision, ~1mm) */
  wgs_long: number;
  /** WGS84 height in metres (4dp precision, 0.1mm) */
  wgs_height: number | null;
  /** OSGB eastings in metres (4dp precision, 0.1mm) */
  osgb_eastings: number;
  /** OSGB northings in metres (4dp precision, 0.1mm) */
  osgb_northings: number;
  osgb_gridref: string;
  /** OSGB height in metres (4dp precision, 0.1mm) */
  osgb_height: number | null;
  /** Grid system: 'gb' (OSGB36) or 'ie' (Irish Grid) */
  grid_system?: 'gb' | 'ie';
  /** Country name (e.g., 'England', 'Ireland') */
  country_name?: string;
  postcode: string;
  county: string;
  town: string;
  needs_attention: number;
  attention_comment: string;
  upd_timestamp?: string;
  legal_message: string | null;
}

export interface TrigAdminUpdate {
  name: string;
  fb_number: string;
  stn_number: string;
  stn_number_active: string;
  stn_number_passive: string;
  stn_number_osgb36: string;
  status_id: number;
  type_id: number | null;
  current_use: string;
  historic_use: string;
  condition: string;
  /** WGS84 latitude (8dp precision, ~1mm) */
  wgs_lat: number | string;
  /** WGS84 longitude (8dp precision, ~1mm) */
  wgs_long: number | string;
  /** WGS84 height in metres (4dp precision, 0.1mm) */
  wgs_height: number | null;
  /** OSGB eastings in metres (4dp precision, 0.1mm) */
  osgb_eastings: number | string;
  /** OSGB northings in metres (4dp precision, 0.1mm) */
  osgb_northings: number | string;
  osgb_gridref: string;
  /** OSGB height in metres (4dp precision, 0.1mm) */
  osgb_height: number | null;
  legal_message: string | null;
  action: "solved" | "revisit" | "cant_fix";
  admin_comment: string;
}

export interface TrigAdminCreate {
  name: string;
  fb_number: string;
  stn_number: string;
  stn_number_active: string;
  stn_number_passive: string;
  stn_number_osgb36: string;
  status_id: number;
  type_id: number | null;
  current_use: string;
  historic_use: string;
  condition: string;
  /** WGS84 latitude (8dp precision, ~1mm) */
  wgs_lat: number | string;
  /** WGS84 longitude (8dp precision, ~1mm) */
  wgs_long: number | string;
  /** WGS84 height in metres (4dp precision, 0.1mm) */
  wgs_height: number | null;
  /** OSGB eastings in metres (4dp precision, 0.1mm) */
  osgb_eastings: number | string;
  /** OSGB northings in metres (4dp precision, 0.1mm) */
  osgb_northings: number | string;
  osgb_gridref: string;
  /** OSGB height in metres (4dp precision, 0.1mm) */
  osgb_height: number | null;
  legal_message: string | null;
  admin_comment: string;
}

export interface StatusRecord {
  id: number;
  name: string;
  descr: string;
  limit_descr: string;
}

/**
 * Get summary of trigpoints needing attention
 */
export async function fetchNeedsAttentionSummary(
  token: string
): Promise<TrigNeedsAttentionSummary> {
  return apiGet<TrigNeedsAttentionSummary>(
    `/v1/admin/trigs/needs-attention/summary`,
    token
  );
}

/**
 * Get paginated list of trigpoints needing attention
 */
export async function fetchNeedsAttentionTrigs(
  params: { skip?: number; limit?: number },
  token: string
): Promise<TrigNeedsAttentionListResponse> {
  const skip = params.skip ?? 0;
  const limit = params.limit ?? 20;
  return apiGet<TrigNeedsAttentionListResponse>(
    `/v1/admin/trigs/needs-attention?skip=${skip}&limit=${limit}`,
    token
  );
}

/**
 * Get trigpoint details for admin editing
 */
export async function fetchTrigForEdit(
  trigId: number,
  token: string
): Promise<TrigAdminDetail> {
  return apiGet<TrigAdminDetail>(`/v1/admin/trigs/${trigId}`, token);
}

/**
 * Update trigpoint with admin privileges
 */
export async function updateTrigAdmin(
  trigId: number,
  data: TrigAdminUpdate,
  token: string
): Promise<TrigAdminDetail> {
  return apiPatch<TrigAdminDetail>(`/v1/admin/trigs/${trigId}`, data, token);
}

/**
 * Create a new trigpoint with admin privileges
 */
export async function createTrigAdmin(
  data: TrigAdminCreate,
  token: string
): Promise<TrigAdminDetail> {
  return apiPost<TrigAdminDetail>(`/v1/admin/trigs`, data, token);
}

/**
 * Get all status records for dropdowns
 */
export async function fetchStatuses(token: string): Promise<StatusRecord[]> {
  return apiGet<StatusRecord[]>(`/v1/admin/statuses`, token);
}

// Merge Users Types and Functions

export interface AdminMergeUsersRequest {
  target_user_id: number;
  source_user_id: number;
  dry_run: boolean;
}

export interface MergeRecordCounts {
  tlog: number;
  tphoto: number;
  tphotovote: number;
}

export interface AdminMergeUsersPreview {
  dry_run: true;
  target_user: Record<string, string | number | null | undefined>;
  source_user: Record<string, string | number | null | undefined>;
  estimated_records: MergeRecordCounts;
  profile_updates: Record<string, string | null>;
  auth0_will_update: boolean;
}

export interface AdminMergeUsersResponse {
  success: boolean;
  target_user_id: number;
  source_user_id: number;
  updated_records: MergeRecordCounts;
  profile_updated: boolean;
  auth0_updated: boolean;
}

/**
 * Merge source user into target user (admin only)
 */
export async function mergeUsers(
  payload: AdminMergeUsersRequest,
  token: string
): Promise<AdminMergeUsersPreview | AdminMergeUsersResponse> {
  return apiPost<AdminMergeUsersPreview | AdminMergeUsersResponse>(
    `/v1/admin/merge-users`,
    payload,
    token
  );
}

// Logs Needing Attention Types and Functions

export interface LogNeedsAttentionSummary {
  orphaned_count: number;
  duplicate_count: number;
}

export interface OrphanedLogItem {
  id: number;
  trig_id: number | null;
  user_id: number | null;
  user_name: string | null;
  date: string | null;
  time: string | null;
  condition: string | null;
  comment: string | null;
  score: number | null;
  issue_type: "orphaned";
}

export interface DuplicateLogItem {
  trig_id: number | null;
  trig_name: string | null;
  trig_waypoint: string | null;
  user_id: number | null;
  user_name: string | null;
  date: string | null;
  duplicate_count: number;
  logs: DuplicateLogGroupEntry[];
  issue_type: "duplicate";
}

export interface DuplicateLogGroupEntry {
  id: number;
  time: string | null;
  condition: string | null;
  comment: string | null;
  score: number | null;
}

export type LogNeedsAttentionItem = OrphanedLogItem | DuplicateLogItem;

export interface LogNeedsAttentionListResponse {
  items: LogNeedsAttentionItem[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

/**
 * Get summary of logs needing attention (admin only)
 */
export async function fetchLogsNeedsAttentionSummary(
  token: string
): Promise<LogNeedsAttentionSummary> {
  return apiGet<LogNeedsAttentionSummary>(
    `/v1/admin/logs/needs-attention/summary`,
    token
  );
}

/**
 * Get paginated list of logs needing attention (admin only)
 */
export async function fetchLogsNeedsAttention(
  params: { skip?: number; limit?: number },
  token: string
): Promise<LogNeedsAttentionListResponse> {
  const skip = params.skip ?? 0;
  const limit = params.limit ?? 50;
  return apiGet<LogNeedsAttentionListResponse>(
    `/v1/admin/logs/needs-attention?skip=${skip}&limit=${limit}`,
    token
  );
}

/**
 * Delete an orphaned log (admin only)
 */
export async function deleteOrphanedLog(
  logId: number,
  token: string
): Promise<{ success: boolean; message: string }> {
  return apiDelete<{ success: boolean; message: string }>(
    `/v1/admin/logs/${logId}/orphaned`,
    token
  );
}

/**
 * Delete a duplicate log (admin only)
 */
export async function deleteDuplicateLog(
  logId: number,
  token: string
): Promise<{ success: boolean; message: string }> {
  return apiDelete<{ success: boolean; message: string }>(
    `/v1/admin/logs/${logId}/duplicate`,
    token
  );
}

// ============================================================================
// Coordinate Conversion
// ============================================================================

/**
 * Request parameters for coordinate conversion.
 */
export interface CoordinateConversionRequest {
  from: "wgs84" | "osgb" | "irish";
  to: "wgs84" | "osgb" | "irish" | "grid";  // "grid" = auto-detect based on location
  lat?: number;
  lon?: number;
  e?: number;
  n?: number;
  height?: number;
}

/**
 * Input coordinates in the conversion response.
 */
export interface CoordinateInput {
  lat?: number;
  lon?: number;
  e?: number;
  n?: number;
  height?: number;
  gridref?: string;
}

/**
 * Output coordinates in the conversion response.
 */
export interface CoordinateOutput {
  lat?: number;
  lon?: number;
  e?: number;
  n?: number;
  height?: number;
  gridref?: string;
}

/**
 * Response from the coordinate conversion endpoint.
 */
export interface CoordinateConversionResponse {
  from_crs: string;
  to_crs: string;
  input: CoordinateInput;
  output: CoordinateOutput;
  /** Grid system used: 'gb' (OSGB36) or 'ie' (Irish Grid) */
  grid_system?: 'gb' | 'ie';
  /** Country name if auto-detected (e.g., 'Ireland', 'England') */
  country_name?: string;
}

/**
 * Convert coordinates between WGS84 and OSGB36 using OSTN15/OSGM15.
 *
 * This endpoint is public (no authentication required).
 *
 * @example
 * // WGS84 to OSGB (2D)
 * const result = await convertCoordinates({
 *   from: "wgs84",
 *   to: "osgb",
 *   lat: 51.5074,
 *   lon: -0.1276,
 * });
 *
 * @example
 * // WGS84 to OSGB (3D with height)
 * const result = await convertCoordinates({
 *   from: "wgs84",
 *   to: "osgb",
 *   lat: 51.5074,
 *   lon: -0.1276,
 *   height: 100, // ellipsoidal height
 * });
 *
 * @example
 * // OSGB to WGS84
 * const result = await convertCoordinates({
 *   from: "osgb",
 *   to: "wgs84",
 *   e: 530034,
 *   n: 179382,
 * });
 */
export async function convertCoordinates(
  params: CoordinateConversionRequest
): Promise<CoordinateConversionResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("from", params.from);
  searchParams.set("to", params.to);

  if (params.lat !== undefined) {
    searchParams.set("lat", params.lat.toString());
  }
  if (params.lon !== undefined) {
    searchParams.set("lon", params.lon.toString());
  }
  if (params.e !== undefined) {
    searchParams.set("e", params.e.toString());
  }
  if (params.n !== undefined) {
    searchParams.set("n", params.n.toString());
  }
  if (params.height !== undefined) {
    searchParams.set("height", params.height.toString());
  }

  return apiGet<CoordinateConversionResponse>(
    `/v1/coordinates/convert?${searchParams.toString()}`
  );
}


// ============================================================================
// Types Admin API
// ============================================================================

/**
 * Trig type within a category
 */
export interface TrigType {
  id: number;
  category_id: number;
  code: string;
  name: string;
  description: string | null;
  wiki_url: string | null;
  sort_order: number;
}

/**
 * Trig type with nested category
 */
export interface TrigTypeWithCategory extends TrigType {
  category: TrigCategory;
}

/**
 * Trig category (high-level grouping)
 */
export interface TrigCategory {
  id: number;
  code: string;
  name: string;
  description: string | null;
  wiki_url: string | null;
  sort_order: number;
}

/**
 * Trig category with nested types
 */
export interface TrigCategoryWithTypes extends TrigCategory {
  types: TrigType[];
}

/**
 * Input for creating a new category
 */
export interface TrigCategoryCreateInput {
  code: string;
  name: string;
  description?: string | null;
  wiki_url?: string | null;
  sort_order?: number | null;
}

/**
 * Input for updating a category
 */
export interface TrigCategoryUpdateInput {
  code?: string;
  name?: string;
  description?: string | null;
  wiki_url?: string | null;
  sort_order?: number;
}

/**
 * Input for creating a new type
 */
export interface TrigTypeCreateInput {
  category_id: number;
  code: string;
  name: string;
  description?: string | null;
  wiki_url?: string | null;
  sort_order?: number | null;
  legacy_physical_type?: string | null;
}

/**
 * Input for updating a type
 */
export interface TrigTypeUpdateInput {
  category_id?: number;
  code?: string;
  name?: string;
  description?: string | null;
  wiki_url?: string | null;
  sort_order?: number;
  legacy_physical_type?: string | null;
}

/**
 * Type usage information
 */
export interface TrigTypeUsage {
  type_id: number;
  type_code: string;
  type_name: string;
  usage_count: number;
}

/**
 * Get all categories with their types (admin)
 */
export async function fetchCategoriesWithTypes(
  token: string
): Promise<TrigCategoryWithTypes[]> {
  return apiGet<TrigCategoryWithTypes[]>(`/v1/admin/types/categories`, token);
}

/**
 * Create a new category (admin)
 */
export async function createCategory(
  data: TrigCategoryCreateInput,
  token: string
): Promise<TrigCategory> {
  return apiPost<TrigCategory>(`/v1/admin/types/categories`, data, token);
}

/**
 * Update an existing category (admin)
 */
export async function updateCategory(
  categoryId: number,
  data: TrigCategoryUpdateInput,
  token: string
): Promise<TrigCategory> {
  return apiPatch<TrigCategory>(
    `/v1/admin/types/categories/${categoryId}`,
    data,
    token
  );
}

/**
 * Delete a category (admin)
 * Will fail if any types are assigned to this category.
 */
export async function deleteCategory(
  categoryId: number,
  token: string
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(
    `${apiBase}/v1/admin/types/categories/${categoryId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
}

/**
 * Reorder categories (admin)
 */
export async function reorderCategories(
  order: number[],
  token: string
): Promise<TrigCategory[]> {
  return apiPost<TrigCategory[]>(
    `/v1/admin/types/categories/reorder`,
    { order },
    token
  );
}

/**
 * Create a new type (admin)
 */
export async function createType(
  data: TrigTypeCreateInput,
  token: string
): Promise<TrigTypeWithCategory> {
  return apiPost<TrigTypeWithCategory>(`/v1/admin/types/types`, data, token);
}

/**
 * Update an existing type (admin)
 */
export async function updateType(
  typeId: number,
  data: TrigTypeUpdateInput,
  token: string
): Promise<TrigTypeWithCategory> {
  return apiPatch<TrigTypeWithCategory>(
    `/v1/admin/types/types/${typeId}`,
    data,
    token
  );
}

/**
 * Delete a type (admin)
 * Will fail if any trigpoints are using this type.
 */
export async function deleteType(
  typeId: number,
  token: string
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/admin/types/types/${typeId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
}

/**
 * Reorder types within a category (admin)
 */
export async function reorderTypes(
  categoryId: number,
  order: number[],
  token: string
): Promise<TrigType[]> {
  return apiPost<TrigType[]>(
    `/v1/admin/types/types/reorder`,
    { category_id: categoryId, order },
    token
  );
}

/**
 * Get usage count for a type (admin)
 */
export async function fetchTypeUsage(
  typeId: number,
  token: string
): Promise<TrigTypeUsage> {
  return apiGet<TrigTypeUsage>(`/v1/admin/types/types/${typeId}/usage`, token);
}

// ============================================================================
// Status Admin Types and Functions
// ============================================================================

/**
 * Status record
 */
export interface Status {
  id: number;
  name: string;
  descr: string;
  limit_descr: string;
}

/**
 * Input for creating a new status
 */
export interface StatusCreateInput {
  id: number;
  name: string;
  descr: string;
  limit_descr: string;
}

/**
 * Input for updating a status
 */
export interface StatusUpdateInput {
  name?: string;
  descr?: string;
  limit_descr?: string;
}

/**
 * Status usage response
 */
export interface StatusUsage {
  status_id: number;
  usage_count: number;
}

/**
 * Get all statuses (admin)
 */
export async function fetchAllStatuses(token: string): Promise<Status[]> {
  return apiGet<Status[]>(`/v1/admin/status/statuses`, token);
}

/**
 * Create a new status (admin)
 */
export async function createStatus(
  data: StatusCreateInput,
  token: string
): Promise<Status> {
  return apiPost<Status>(`/v1/admin/status/statuses`, data, token);
}

/**
 * Update a status (admin)
 */
export async function updateStatus(
  statusId: number,
  data: StatusUpdateInput,
  token: string
): Promise<Status> {
  return apiPatch<Status>(`/v1/admin/status/statuses/${statusId}`, data, token);
}

/**
 * Delete a status (admin)
 * Will fail if any trigpoints are using this status.
 */
export async function deleteStatus(
  statusId: number,
  token: string
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/admin/status/statuses/${statusId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
}

/**
 * Get usage count for a status (admin)
 */
export async function fetchStatusUsage(
  statusId: number,
  token: string
): Promise<StatusUsage> {
  return apiGet<StatusUsage>(`/v1/admin/status/statuses/${statusId}/usage`, token);
}

// ============================================================================
// Condition Admin Types and Functions
// ============================================================================

/**
 * Condition record
 */
export interface Condition {
  code: string;
  name: string;
  description: string | null;
  icon_file: string | null;
  trig_colour: string | null;
  log_colour: string | null;
  similar_codes: string | null;
  wiki_url: string | null;
  sort_order: number;
}

/**
 * Input for creating a new condition
 */
export interface ConditionCreateInput {
  code: string;
  name: string;
  sort_order: number;
  description?: string;
  icon_file?: string;
  trig_colour?: string;
  log_colour?: string;
  similar_codes?: string;
  wiki_url?: string;
}

/**
 * Input for updating a condition
 */
export interface ConditionUpdateInput {
  name?: string;
  description?: string;
  icon_file?: string;
  trig_colour?: string;
  log_colour?: string;
  similar_codes?: string;
  wiki_url?: string;
  sort_order?: number;
}

/**
 * Condition usage response
 */
export interface ConditionUsage {
  code: string;
  usage_count: number;
}

/**
 * Get all conditions (admin)
 */
export async function fetchAllConditions(token: string): Promise<Condition[]> {
  return apiGet<Condition[]>(`/v1/admin/condition/conditions`, token);
}

/**
 * Create a new condition (admin)
 */
export async function createCondition(
  data: ConditionCreateInput,
  token: string
): Promise<Condition> {
  return apiPost<Condition>(`/v1/admin/condition/conditions`, data, token);
}

/**
 * Update a condition (admin)
 */
export async function updateCondition(
  code: string,
  data: ConditionUpdateInput,
  token: string
): Promise<Condition> {
  return apiPatch<Condition>(`/v1/admin/condition/conditions/${code}`, data, token);
}

/**
 * Delete a condition (admin)
 * Will fail if any logs are using this condition.
 */
export async function deleteCondition(
  code: string,
  token: string
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/admin/condition/conditions/${code}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
}

/**
 * Get usage count for a condition (admin)
 */
export async function fetchConditionUsage(
  code: string,
  token: string
): Promise<ConditionUsage> {
  return apiGet<ConditionUsage>(`/v1/admin/condition/conditions/${code}/usage`, token);
}

// ============================================================================
// Public Conditions API (no auth required)
// ============================================================================

/**
 * Get all conditions (public, cached)
 */
export async function fetchPublicConditions(): Promise<Condition[]> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/conditions`);
  if (!response.ok) {
    throw new Error("Failed to fetch conditions");
  }
  return response.json();
}

/**
 * Get a single condition by code (public, cached)
 */
export async function fetchPublicConditionByCode(
  code: string
): Promise<Condition> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/conditions/${code}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch condition ${code}`);
  }
  return response.json();
}

// ============================================================================
// OS Net Comparison Types and Functions (admin)
// ============================================================================

export interface OSNetStationData {
  code?: string;
  easting?: number;
  northing?: number;
  gridref?: string;
  height?: number;
  lat_dms?: string;
  lon_dms?: string;
}

export interface DBStationData {
  trig_id?: number;
  waypoint?: string;
  name?: string;
  stn_number_active?: string;
  easting?: number;
  northing?: number;
  gridref?: string;
  height?: number;
}

export interface StationDifference {
  station_code: string;
  difference_type: 
    | "new_in_osnet" 
    | "missing_from_osnet" 
    | "coordinate_mismatch" 
    | "unmatched_db"
    | "destroyed_not_in_db"
    | "legacy_not_in_db";
  description: string;
  osnet_data?: OSNetStationData;
  db_data?: DBStationData;
  distance_metres?: number;
  osnet_section?: number;
  osnet_section_name?: string;
}

export interface OSNetComparisonResponse {
  osnet_count: number;
  osnet_current_count: number;
  osnet_legacy_count: number;
  osnet_destroyed_count: number;
  db_count: number;
  matched_count: number;
  differences: StationDifference[];
  osnet_fetch_time: string;
  changelog_entries: string[];
  new_in_osnet_count: number;
  missing_from_osnet_count: number;
  coordinate_mismatch_count: number;
  unmatched_db_count: number;
  destroyed_not_in_db_count: number;
  legacy_not_in_db_count: number;
}

/**
 * Fetch OS Net comparison data (admin)
 */
export async function fetchOSNetComparison(
  token: string,
  forceRefresh: boolean = false
): Promise<OSNetComparisonResponse> {
  const params = forceRefresh ? "?force_refresh=true" : "";
  return apiGet<OSNetComparisonResponse>(`/v1/admin/osnet/comparison${params}`, token);
}

/**
 * Clear OS Net cache (admin)
 */
export async function clearOSNetCache(token: string): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/admin/osnet/cache/clear`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }
}

