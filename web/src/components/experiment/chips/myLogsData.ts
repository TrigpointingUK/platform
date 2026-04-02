/**
 * Shared data constants for the MyLogsChip filter.
 *
 * Separated from the component file so react-refresh works correctly.
 */

export const LOGGED_CONDITION_VALUES = [
  { code: "G", label: "Good", icon: "c_good.png", mapIcon: "mapicon_pillar_green.png" },
  { code: "S", label: "Slightly Damaged", icon: "c_slightlydamaged.png", mapIcon: "mapicon_pillar_yellow.png" },
  { code: "D", label: "Damaged", icon: "c_damaged.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "T", label: "Toppled", icon: "c_toppled.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "C", label: "Converted", icon: "c_slightlydamaged.png", mapIcon: "mapicon_pillar_yellow.png" },
  { code: "R", label: "Remains", icon: "c_toppled.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "X", label: "Destroyed", icon: "c_definitelymissing.png", mapIcon: "mapicon_pillar_red.png" },
  { code: "V", label: "Unreachable but Visible", icon: "c_unreachablebutvisible.png", mapIcon: "mapicon_pillar_yellow.png" },
  { code: "P", label: "Inaccessible", icon: "c_unknown.png", mapIcon: "mapicon_pillar_grey.png" },
  { code: "U", label: "Unknown", icon: "c_unknown.png", mapIcon: "mapicon_pillar_grey.png" },
  { code: "Q", label: "Possibly Missing", icon: "c_possiblymissing.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "N", label: "Couldn't Find", icon: "c_possiblymissing.png", mapIcon: "mapicon_pillar_grey.png" },
];

export const ALL_LOGGED_CONDITION_CODES = LOGGED_CONDITION_VALUES.map(c => c.code);
