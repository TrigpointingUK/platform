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

export interface Log {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
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


