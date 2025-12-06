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
 * Based on legacy PHP code condition mappings (see api/utils/condition_mapping.py)
 */
export type ConditionCode = 
  | 'G'  // Good
  | 'S'  // Slightly damaged
  | 'C'  // Converted
  | 'D'  // Damaged
  | 'R'  // Remains
  | 'T'  // Toppled
  | 'M'  // Moved
  | 'Q'  // Possibly missing
  | 'X'  // Destroyed
  | 'V'  // Unreachable but visible
  | 'P'  // Inaccessible
  | 'N'  // Couldn't find it
  | 'U'  // Unknown (fallback)
  | 'Z'; // Not Logged

/**
 * User log status for a trigpoint
 */
export interface UserLogStatus {
  hasLogged: boolean;
  condition?: string; // Condition code from the user's log
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
 * GREEN (Good/Minor damage):
 * - G = Good
 * - S = Slightly damaged
 * 
 * YELLOW (Damaged/Compromised):
 * - C = Converted
 * - D = Damaged
 * - R = Remains
 * - T = Toppled
 * - M = Moved
 * - V = Unreachable but visible
 * 
 * RED (Missing/Destroyed):
 * - Q = Possibly missing
 * - X = Destroyed
 * - N = Couldn't find it
 * 
 * GREY (Unknown/Inaccessible):
 * - P = Inaccessible
 * - U = Unknown
 * - Z = Not Logged
 */
const CONDITION_TO_COLOR: Record<ConditionCode, IconColor> = {
  // Good/minor damage condition (green)
  'G': 'green',
  'S': 'green',
  // Damaged/compromised condition (yellow)
  'C': 'yellow',
  'D': 'yellow',
  'R': 'yellow',
  'T': 'yellow',
  'M': 'yellow',
  'V': 'yellow',
  // Missing/destroyed condition (red)
  'Q': 'red',
  'X': 'red',
  'N': 'red',
  // Unknown/inaccessible condition (grey)
  'P': 'grey',
  'U': 'grey',
  'Z': 'grey',
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
 * 
 * For userLog mode, colors are based on the condition reported in the user's log:
 * - Green: Found in good/minor damage condition (G, S), or not logged/empty (Z, empty/null)
 * - Yellow: Found but damaged/compromised (C, D, R, T, M, V)
 * - Red: Missing/destroyed (Q, X, N), plus P, U when logged
 * - Grey: Not logged by the user
 * 
 * Special case: Unknown/inaccessible conditions (P, U) count as "red" 
 * in userLog mode (vs grey in condition mode) because the user made the effort to log it.
 * 
 * Special case: Empty/null and Z (Not Logged) count as "green" - the user logged but
 * didn't specify a condition, which typically means it was fine.
 */
export const getUserLogColor = (logStatus: UserLogStatus): IconColor => {
  if (!logStatus.hasLogged) {
    return 'grey';
  }
  
  // Get the condition from the log
  const condition = logStatus.condition || '';
  const upperCondition = condition.toUpperCase();
  
  // Special case: Empty/null or Z (Not Logged) counts as "green" for userLog mode
  // The user logged but didn't specify a condition, which typically means it was fine
  if (upperCondition === '' || upperCondition === 'Z') {
    return 'green';
  }
  
  // Special case: Unknown/inaccessible conditions count as "red" for userLog mode
  // because user made the effort to log it, even if they couldn't determine condition
  if (upperCondition === 'P' || upperCondition === 'U') {
    return 'red';
  }
  
  // Otherwise use standard condition-to-color mapping
  return getConditionColor(condition);
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
    { color: 'green', label: 'Good/slightly damaged' },
    { color: 'yellow', label: 'Damaged/compromised' },
    { color: 'red', label: 'Missing or destroyed' },
    { color: 'grey', label: 'Unknown/inaccessible' },
  ],
  userLog: [
    { color: 'green', label: 'Logged' },
    { color: 'yellow', label: 'Logged - damaged/compromised' },
    { color: 'red', label: 'Logged - missing/destroyed/inaccessible' },
    { color: 'grey', label: 'Not logged by you' },
  ],
} as const;

