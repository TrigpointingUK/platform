/**
 * The trig list filter: "in" keeps trigs on any of the lists, "not_in" keeps
 * trigs on none of them, "all" is no filter.
 */
export type ListFilterMode = "all" | "in" | "not_in";

export interface ListFilter {
  mode: ListFilterMode;
  listIds: number[];
}

export const NO_LIST_FILTER: ListFilter = { mode: "all", listIds: [] };
