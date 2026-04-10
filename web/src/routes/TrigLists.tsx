import { useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import { useAuth0 } from "@auth0/auth0-react";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import { TrigCard } from "../components/trigs/TrigCard";
import { useMyLists, useListItems, type TrigListFull } from "../hooks/useTrigLists";
import { useUserProfile } from "../hooks/useUserProfile";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export default function TrigLists() {
  const { listId: listIdParam } = useParams<{ listId?: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, loginWithRedirect } = useAuth0();

  const { data: lists, isLoading: isListsLoading } = useMyLists();
  const { data: userProfile } = useUserProfile("me");
  const distanceUnit = (userProfile?.prefs?.distance_ind as "K" | "M") ?? "K";

  const selectedListId = useMemo(() => {
    if (listIdParam) return parseInt(listIdParam, 10);
    if (lists && lists.length > 0) {
      const defaultList = lists.find((l) => l.is_default) ?? lists[0];
      return defaultList.id;
    }
    return null;
  }, [listIdParam, lists]);

  const selectedList = lists?.find((l) => l.id === selectedListId) ?? null;

  useDocumentTitle(
    selectedList
      ? `${selectedList.name} | Lists | TrigpointingUK`
      : "Lists | TrigpointingUK",
  );

  const {
    data: itemsData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: isItemsLoading,
  } = useListItems(selectedListId);

  const { ref: loadMoreRef, inView } = useInView({ threshold: 0, rootMargin: "200px" });

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const allItems = itemsData?.pages.flatMap((page) => page.items) ?? [];

  if (!isAuthenticated) {
    return (
      <>
        <title>Lists | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Sign in to view and manage your trig lists.
              </p>
              <button
                onClick={() => loginWithRedirect({ appState: { returnTo: "/lists" } })}
                className="px-4 py-2 bg-trig-green-600 text-white rounded-md hover:bg-trig-green-700"
              >
                Sign In
              </button>
            </div>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <title>{selectedList ? `${selectedList.name} | Lists` : "Lists"} | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Lists</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Browse your saved trigpoint collections.
          </p>
        </div>

        {/* List selector */}
        {isListsLoading ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : lists && lists.length > 0 ? (
          <>
            <div className="mb-4">
              <select
                value={selectedListId ?? ""}
                onChange={(e) => {
                  navigate(`/lists/${e.target.value}`, { replace: true });
                }}
                className="w-full sm:w-auto px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-trig-green-500 focus:border-trig-green-500"
              >
                {lists.map((list: TrigListFull) => (
                  <option key={list.id} value={list.id}>
                    {list.name} ({list.item_count})
                  </option>
                ))}
              </select>
            </div>

            {/* Items */}
            <Card>
              {isItemsLoading ? (
                <div className="flex justify-center py-8">
                  <Spinner size="lg" />
                </div>
              ) : allItems.length > 0 ? (
                <div>
                  {allItems.map((item) =>
                    item.trig ? (
                      <TrigCard
                        key={item.id}
                        trig={{
                          id: item.trig.id,
                          waypoint: item.trig.waypoint,
                          name: item.trig.name,
                          condition: item.trig.condition ?? "U",
                          wgs_lat: item.trig.wgs_lat ?? "0",
                          wgs_long: item.trig.wgs_long ?? "0",
                          osgb_gridref: item.trig.osgb_gridref ?? "",
                          type_code: item.trig.type_code ?? undefined,
                          type_name: item.trig.type_name ?? undefined,
                          category_code: item.trig.category_code ?? undefined,
                          category_name: item.trig.category_name ?? undefined,
                          status_name: item.trig.status_name ?? undefined,
                          wgs_height: item.trig.wgs_height ?? undefined,
                          score: item.trig.score ?? undefined,
                        }}
                        showDistance={false}
                        distanceUnit={distanceUnit}
                      />
                    ) : null,
                  )}

                  {/* Infinite scroll sentinel */}
                  <div ref={loadMoreRef} className="py-4 text-center">
                    {isFetchingNextPage && <Spinner size="sm" />}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <p className="text-lg mb-2">This list is empty</p>
                  <p className="text-sm">
                    Use the star button on a trigpoint page to add trigs to your lists.
                  </p>
                </div>
              )}
            </Card>
          </>
        ) : (
          <Card>
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <p className="text-lg mb-2">No lists yet</p>
              <p className="text-sm">
                Use the star button on a trigpoint page to get started, or create a list
                in your <a href="/preferences" className="text-trig-green-600 hover:underline">preferences</a>.
              </p>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
