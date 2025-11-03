const API_BASE = import.meta.env.VITE_API_BASE as string;

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
  const res = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
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

export interface TrigDetails {
  current_use: string;
  historic_use: string;
  wgs_height: number;
  postcode: string;
  county: string;
  town: string;
  fb_number: string;
  stn_number: string;
  stn_number_active?: string;
  stn_number_passive?: string;
  stn_number_osgb36?: string;
}

export interface TrigStats {
  logged_first: string;
  logged_last: string;
  logged_count: number;
  found_last: string;
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
  physical_type: string;
  condition: string;
  wgs_lat: string;
  wgs_long: string;
  osgb_gridref: string;
  details?: TrigDetails;
  stats?: TrigStats;
}

