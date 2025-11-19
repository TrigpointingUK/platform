/**
 * Map icon configuration and utilities
 * 
 * @stable - These types and functions determine marker appearance on all maps.
 * Changes can affect visual consistency across the application.
 * 
 * Maps physical types to icon filenames and handles color modes for markers.
 * 
 * @remarks
 * Breaking changes to consider:
 * - Changing IconColorMode type values
 * - Modifying icon file naming conventions
 * - Changing color mapping logic
 * - Altering function signatures
 * 
 * Non-breaking changes:
 * - Adding new physical types
 * - Adding new color modes (with fallback)
 * - Performance improvements
 * - Internal refactoring
 */

/**
 * Icon color modes
 * @stable
 */
export type IconColorMode = 'condition' | 'userLog';

/**
 * Available icon colors
 */
export type IconColor = 'green' | 'yellow' | 'red' | 'grey';

/**
 * Trig condition codes
 */
export type ConditionCode = 
  | 'G'  // Good
  | 'D'  // Damaged  
  | 'M'  // Missing
  | 'P'  // Possibly Missing
  | 'U'  // Unknown
  | 'S'  // Slightly Damaged
  | 'Q'  // Questionable
  | 'X'  // Possibly Damaged
  | 'T'  // Toppled
  | 'C'  // Cracked
  | 'R'  // Restored
  | 'E'  // Excellent
  | 'N'; // Not Found

/**
 * User log status for a trigpoint
 */
export interface UserLogStatus {
  hasLogged: boolean;
  foundStatus?: boolean; // true = found, false = not found
}

/**
 * Map physical types to icon base names
 * 
 * Based on available icons in res/icons/:
 * - pillar
 * - fbm
 * - passive
 * - intersected
 */
const PHYSICAL_TYPE_TO_ICON: Record<string, string> = {
  'Pillar': 'pillar',
  'FBM': 'fbm',
  'Flush Bracket': 'fbm',
  'Passive Station': 'passive',
  'Passive station': 'passive',
  'Intersection': 'intersected',
  'Intersected Station': 'intersected',
  // Fallbacks for types without specific icons
  'Bolt': 'pillar',
  'Active Station': 'passive',
  'Other': 'pillar',
};

/**
 * Map condition codes to colors
 * 
 * GREEN (Good):
 * - G = Good
 * - E = Excellent
 * - R = Restored
 * 
 * YELLOW (Damaged):
 * - D = Damaged
 * - S = Slightly Damaged
 * - C = Cracked
 * - X = Possibly Damaged
 * - T = Toppled
 * 
 * RED (Missing):
 * - M = Missing
 * - P = Possibly Missing
 * - N = Not Found
 * 
 * GREY (Unknown):
 * - U = Unknown
 * - Q = Questionable
 */
const CONDITION_TO_COLOR: Record<ConditionCode, IconColor> = {
  // Good condition (green)
  'G': 'green',
  'E': 'green',
  'R': 'green',
  // Damaged condition (yellow)
  'D': 'yellow',
  'S': 'yellow',
  'C': 'yellow',
  'X': 'yellow',
  'T': 'yellow',
  // Missing condition (red)
  'M': 'red',
  'P': 'red',
  'N': 'red',
  // Unknown condition (grey)
  'U': 'grey',
  'Q': 'grey',
};

/**
 * Get icon base name for a physical type
 */
export const getIconBaseName = (physicalType: string): string => {
  return PHYSICAL_TYPE_TO_ICON[physicalType] || 'pillar';
};

/**
 * Get color for condition mode
 */
export const getConditionColor = (condition: string): IconColor => {
  const code = condition.toUpperCase() as ConditionCode;
  return CONDITION_TO_COLOR[code] || 'grey';
};

/**
 * Get color for user log mode
 */
export const getUserLogColor = (logStatus: UserLogStatus): IconColor => {
  if (!logStatus.hasLogged) {
    return 'grey';
  }
  
  // If logged but foundStatus not available, assume found
  if (logStatus.foundStatus === undefined || logStatus.foundStatus === true) {
    return 'green';
  }
  
  return 'red'; // Not found
};

/**
 * Get the full icon URL for a trigpoint
 * 
 * @param physicalType - Physical type of the trigpoint
 * @param color - Icon color
 * @param highlighted - Whether to use highlighted version (_h suffix)
 * @returns URL path to the icon file
 */
export const getIconUrl = (
  physicalType: string,
  color: IconColor,
  highlighted: boolean = false
): string => {
  const baseName = getIconBaseName(physicalType);
  const highlightSuffix = highlighted ? '_h' : '';
  const filename = `mapicon_${baseName}_${color}${highlightSuffix}.png`;
  
  // Icons are served from /icons/ in public directory
  return `/icons/${filename}`;
};

/**
 * Get icon URL based on color mode
 * 
 * @param physicalType - Physical type of the trigpoint
 * @param condition - Condition code
 * @param colorMode - Icon color mode (condition or userLog)
 * @param logStatus - User's log status for this trig
 * @param highlighted - Whether to highlight the icon
 * @param statusName - Status name (e.g., "Minor mark") - used to override icon type
 */
export const getIconUrlForTrig = (
  physicalType: string,
  condition: string,
  colorMode: IconColorMode,
  logStatus: UserLogStatus | null,
  highlighted: boolean = false,
  statusName?: string
): string => {
  let color: IconColor;
  
  if (colorMode === 'condition') {
    color = getConditionColor(condition);
  } else {
    // User log mode
    if (!logStatus) {
      // If no log status available, fall back to grey
      color = 'grey';
    } else {
      color = getUserLogColor(logStatus);
    }
  }
  
  // Override physical type icon for Minor marks - use passive icon
  let iconPhysicalType = physicalType;
  if (statusName && statusName.trim() === 'Minor mark') {
    iconPhysicalType = 'Passive Station';  // This maps to 'passive' icon
  }
  
  return getIconUrl(iconPhysicalType, color, highlighted);
};

/**
 * Storage key for persisting icon color mode preference
 */
export const ICON_COLOR_MODE_STORAGE_KEY = 'trigpointing_map_icon_color_mode';

/**
 * Default icon color mode
 */
export const DEFAULT_ICON_COLOR_MODE: IconColorMode = 'condition';

/**
 * Get user's preferred icon color mode
 */
export const getPreferredIconColorMode = (): IconColorMode => {
  try {
    const stored = localStorage.getItem(ICON_COLOR_MODE_STORAGE_KEY);
    return (stored as IconColorMode) || DEFAULT_ICON_COLOR_MODE;
  } catch {
    return DEFAULT_ICON_COLOR_MODE;
  }
};

/**
 * Save user's preferred icon color mode
 */
export const setPreferredIconColorMode = (mode: IconColorMode): void => {
  try {
    localStorage.setItem(ICON_COLOR_MODE_STORAGE_KEY, mode);
  } catch (error) {
    console.error('Failed to save icon color mode preference:', error);
  }
};

/**
 * Legend data for icon color modes
 */
export const ICON_LEGENDS = {
  condition: [
    { color: 'green', label: 'Good condition' },
    { color: 'yellow', label: 'Damaged' },
    { color: 'red', label: 'Missing or possibly missing' },
    { color: 'grey', label: 'Unknown condition' },
  ],
  userLog: [
    { color: 'green', label: 'Logged as found' },
    { color: 'red', label: 'Logged as not found' },
    { color: 'grey', label: 'Not logged by you' },
  ],
} as const;

