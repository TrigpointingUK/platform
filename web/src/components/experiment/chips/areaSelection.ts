/**
 * Area selection for the AreaChip filter.
 */

export interface SelectedArea {
  id: number;
  name: string;
  areaTypeId: number;
  areaTypeName: string;
}

/**
 * Toggle an area in the selection. Selecting an area of a different type
 * from the current selection replaces it rather than combining the two.
 */
export function toggleAreaSelection(
  selected: SelectedArea[],
  area: SelectedArea,
): SelectedArea[] {
  if (selected.some((a) => a.id === area.id)) {
    return selected.filter((a) => a.id !== area.id);
  }
  return [...selected.filter((a) => a.areaTypeId === area.areaTypeId), area];
}
