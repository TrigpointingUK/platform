const CATEGORY_TO_ICON: Record<string, string> = {
  PILLAR: "/icons/t_pillar.png",
  FBM: "/icons/t_fbm.png",
  SURVEY_MARK: "/icons/t_passive.png",
  ACTIVE: "/icons/t_active.png",
  INTERSECTED: "/icons/t_intersected.png",
  OTHER: "/icons/t_other.svg",
};

export function getTrigIconUrl(categoryCode?: string): string {
  if (categoryCode && CATEGORY_TO_ICON[categoryCode]) {
    return CATEGORY_TO_ICON[categoryCode];
  }
  return "/icons/t_pillar.png";
}
