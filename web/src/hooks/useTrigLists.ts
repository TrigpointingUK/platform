import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import {
  authenticatedFetch,
  authenticatedGet,
  authenticatedPost,
  authenticatedPatch,
  authenticatedDelete,
} from "../lib/authenticatedFetch";

const API_BASE = import.meta.env.VITE_API_BASE as string;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TrigListSummary {
  id: number;
  name: string;
  item_count: number;
  is_default: boolean;
}

export interface TrigListFull {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
  metadata: Record<string, unknown> | null;
  visibility: string;
  editability: string;
  position: number;
  item_count: number;
  is_default: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface TrigSummary {
  id: number;
  waypoint: string;
  name: string;
  condition: string | null;
  osgb_gridref: string | null;
  wgs_lat: string | null;
  wgs_long: string | null;
  wgs_height: number | null;
  type_code: string | null;
  type_name: string | null;
  category_code: string | null;
  category_name: string | null;
  status_name: string | null;
  score: number | null;
}

export interface TrigListItem {
  id: number;
  list_id: number;
  trig_id: number;
  created_by: number | null;
  updated_by: number | null;
  name: string | null;
  description: string | null;
  metadata: Record<string, unknown> | null;
  position: number;
  created_at: string;
  updated_at: string | null;
  trig: TrigSummary | null;
}

export interface TrigListItemsPage {
  items: TrigListItem[];
  total: number;
  has_more: boolean;
}

export interface TrigListMembership {
  trig_id: number;
  list_ids: number[];
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useMyLists() {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  return useQuery<TrigListFull[]>({
    queryKey: ["trig-lists", "mine"],
    queryFn: () => authenticatedGet<TrigListFull[]>(`${API_BASE}/v1/lists`, getAccessTokenSilently),
    enabled: isAuthenticated,
    staleTime: 30_000,
  });
}

export function useTrigListMembership(trigIds: number[]) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  const idsParam = trigIds.join(",");
  return useQuery<TrigListMembership[]>({
    queryKey: ["trig-lists", "membership", idsParam],
    queryFn: async () => {
      const resp = await authenticatedGet<{ items: TrigListMembership[] }>(
        `${API_BASE}/v1/lists/membership?trig_ids=${idsParam}`,
        getAccessTokenSilently,
      );
      return resp.items;
    },
    enabled: isAuthenticated && trigIds.length > 0,
    staleTime: 30_000,
  });
}

export function useToggleDefaultList(trigId: number) {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<{ action: string; list_id: number; trig_id: number }, Error, void, { prev: TrigListMembership[] | undefined }>({
    mutationFn: () =>
      authenticatedPost(
        `${API_BASE}/v1/lists/default/toggle/${trigId}`,
        {},
        getAccessTokenSilently,
      ),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["trig-lists", "membership"] });
      const membershipKey = ["trig-lists", "membership", String(trigId)];
      const prev = queryClient.getQueryData<TrigListMembership[]>(membershipKey);
      const lists = queryClient.getQueryData<TrigListFull[]>(["trig-lists", "mine"]);
      const defaultList = lists?.find((l) => l.is_default);
      if (defaultList && prev) {
        queryClient.setQueryData<TrigListMembership[]>(membershipKey, (old) =>
          (old ?? []).map((m) => {
            if (m.trig_id !== trigId) return m;
            const ids = m.list_ids.includes(defaultList.id)
              ? m.list_ids.filter((id) => id !== defaultList.id)
              : [...m.list_ids, defaultList.id];
            return { ...m, list_ids: ids };
          }),
        );
      }
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) {
        queryClient.setQueryData(["trig-lists", "membership", String(trigId)], ctx.prev);
      }
      toast.error("Failed to update list");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
    },
  });
}

export function useToggleListItem(trigId: number) {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<
    { action: string; list_id: number; trig_id: number },
    Error,
    { listId: number },
    { prev: TrigListMembership[] | undefined }
  >({
    mutationFn: ({ listId }) =>
      authenticatedPost(
        `${API_BASE}/v1/lists/${listId}/toggle/${trigId}`,
        {},
        getAccessTokenSilently,
      ),
    onMutate: async ({ listId }) => {
      await queryClient.cancelQueries({ queryKey: ["trig-lists", "membership"] });
      const membershipKey = ["trig-lists", "membership", String(trigId)];
      const prev = queryClient.getQueryData<TrigListMembership[]>(membershipKey);
      if (prev) {
        queryClient.setQueryData<TrigListMembership[]>(membershipKey, (old) =>
          (old ?? []).map((m) => {
            if (m.trig_id !== trigId) return m;
            const ids = m.list_ids.includes(listId)
              ? m.list_ids.filter((id) => id !== listId)
              : [...m.list_ids, listId];
            return { ...m, list_ids: ids };
          }),
        );
      }
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) {
        queryClient.setQueryData(["trig-lists", "membership", String(trigId)], ctx.prev);
      }
      toast.error("Failed to update list");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
    },
  });
}

export function useAddToList() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<TrigListItem, Error, { listId: number; trigId: number }>({
    mutationFn: ({ listId, trigId }) =>
      authenticatedPost(
        `${API_BASE}/v1/lists/${listId}/items`,
        { trig_id: trigId },
        getAccessTokenSilently,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
    },
    onError: () => {
      toast.error("Failed to add to list");
    },
  });
}

export function useRemoveFromList() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<void, Error, { listId: number; itemId: number }>({
    mutationFn: ({ listId, itemId }) =>
      authenticatedDelete(
        `${API_BASE}/v1/lists/${listId}/items/${itemId}`,
        getAccessTokenSilently,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
    },
    onError: () => {
      toast.error("Failed to remove from list");
    },
  });
}

export function useCreateList() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<TrigListFull, Error, { name: string }>({
    mutationFn: ({ name }) =>
      authenticatedPost(`${API_BASE}/v1/lists`, { name }, getAccessTokenSilently),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
      toast.success("List created");
    },
    onError: () => {
      toast.error("Failed to create list");
    },
  });
}

export function useDeleteList() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<void, Error, number>({
    mutationFn: (listId) =>
      authenticatedDelete(`${API_BASE}/v1/lists/${listId}`, getAccessTokenSilently),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
      toast.success("List deleted");
    },
    onError: () => {
      toast.error("Failed to delete list");
    },
  });
}

export function useUpdateList() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<
    TrigListFull,
    Error,
    { listId: number; data: Partial<Pick<TrigListFull, "name" | "description" | "visibility" | "editability">> }
  >({
    mutationFn: ({ listId, data }) =>
      authenticatedPatch(`${API_BASE}/v1/lists/${listId}`, data, getAccessTokenSilently),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
    },
    onError: () => {
      toast.error("Failed to update list");
    },
  });
}

export function useListItems(listId: number | null) {
  const PAGE_SIZE = 50;
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  return useInfiniteQuery<TrigListItemsPage>({
    queryKey: ["trig-lists", "items", listId],
    queryFn: async ({ pageParam = 0 }) => {
      const url = `${API_BASE}/v1/lists/${listId}/items?skip=${pageParam}&limit=${PAGE_SIZE}`;
      if (isAuthenticated) {
        return authenticatedGet<TrigListItemsPage>(url, getAccessTokenSilently);
      }
      const resp = await fetch(url);
      if (!resp.ok) throw new Error("Failed to fetch list items");
      return resp.json();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, _allPages, lastPageParam) => {
      if (!lastPage.has_more) return undefined;
      return (lastPageParam as number) + PAGE_SIZE;
    },
    enabled: listId != null,
    staleTime: 30_000,
  });
}

export function useUpdateListItem(listId: number) {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<
    TrigListItem,
    Error,
    { itemId: number; data: { description?: string | null } }
  >({
    mutationFn: ({ itemId, data }) =>
      authenticatedPatch(
        `${API_BASE}/v1/lists/${listId}/items/${itemId}`,
        data,
        getAccessTokenSilently,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists", "items", listId] });
    },
    onError: () => {
      toast.error("Failed to update item");
    },
  });
}

export function useReorderLists() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<void, Error, { ordering: { list_id: number; position: number }[] }>({
    mutationFn: async ({ ordering }) => {
      const response = await authenticatedFetch(
        `${API_BASE}/v1/lists/reorder`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ordering }),
        },
        getAccessTokenSilently,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists", "mine"] });
    },
    onError: () => {
      toast.error("Failed to reorder lists");
    },
  });
}

export function useReorderItems(listId: number) {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<void, Error, { ordering: { item_id: number; position: number }[] }>({
    mutationFn: async ({ ordering }) => {
      const response = await authenticatedFetch(
        `${API_BASE}/v1/lists/${listId}/items/reorder`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ordering }),
        },
        getAccessTokenSilently,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists", "items", listId] });
    },
    onError: () => {
      toast.error("Failed to reorder items");
    },
  });
}

export function useSetDefaultList() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  return useMutation<void, Error, number>({
    mutationFn: async (listId) => {
      await authenticatedPost(
        `${API_BASE}/v1/lists/${listId}/set-default`,
        {},
        getAccessTokenSilently,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trig-lists"] });
      queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
    },
    onError: () => {
      toast.error("Failed to set default list");
    },
  });
}
