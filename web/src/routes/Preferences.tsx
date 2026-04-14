import { useCallback, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { useLocation } from "react-router-dom";
import toast from "react-hot-toast";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import ListsPreferencesPanel from "../components/lists/ListsPreferencesPanel";
import ArchivePreferencesPanel from "../components/archive/ArchivePreferencesPanel";
import {
  useUserProfile,
  updateUserProfile,
  type UserProfile,
  type MapLinkOption,
} from "../hooks/useUserProfile";
import { MAP_LINK_OPTIONS, MAP_LINK_DEFAULTS } from "../lib/mapLinks";

// Trigpoint type categories - matches trig_category table
const TYPE_CATEGORIES = [
  {
    code: "PILLAR",
    name: "Pillar",
    description: "Triangulation pillars",
    icon: "/icons/t_pillar.png",
  },
  {
    code: "FBM",
    name: "FBM",
    description: "Fundamental Bench Marks",
    icon: "/icons/t_fbm.png",
  },
  {
    code: "SURVEY_MARK",
    name: "Survey mark",
    description: "Minor marks (bolts, blocks, rivets)",
    icon: "/icons/t_passive.png",
  },
  {
    code: "INTERSECTED",
    name: "Intersected",
    description: "Church spires, towers, etc.",
    icon: "/icons/t_intersected.png",
  },
  {
    code: "ACTIVE",
    name: "Active station",
    description: "GPS stations",
    icon: "/icons/t_active.png",
  },
  {
    code: "OTHER",
    name: "Other",
    description: "All remaining types",
    icon: "/icons/t_other.svg",
  },
];

// Default categories for new users (Pillar and FBM only)
const DEFAULT_CATEGORIES = ["PILLAR", "FBM"];

export default function Preferences() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently, user: auth0User, isAuthenticated } = useAuth0();
  const location = useLocation();

  const userRoles =
    (auth0User?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  // Fetch current user's profile with preferences
  const { data: user, isLoading, error } = useUserProfile("me");

  // Deep links (e.g. /preferences#data-archive from email): the target id often
  // mounts only after profile loading finishes, so a hash-only dependency runs too
  // early and misses the element. Retry briefly after content is ready.
  useEffect(() => {
    const hash = location.hash;
    if (!hash || hash.length <= 1) return;
    if (isLoading) return;

    const id = hash.slice(1);
    const scrollToTarget = () => {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        return true;
      }
      return false;
    };

    const timers: ReturnType<typeof setTimeout>[] = [];
    const schedule = (delay: number) => {
      timers.push(
        setTimeout(() => {
          scrollToTarget();
        }, delay),
      );
    };

    scrollToTarget();
    schedule(0);
    schedule(50);
    schedule(200);

    return () => timers.forEach(clearTimeout);
  }, [location.hash, location.pathname, isLoading]);

  const handleFieldUpdate = async (field: string, value: string) => {
    try {
      if (field === "distance_ind") {
        await updateUserProfile(
          { distance_ind: value } as Partial<UserProfile>,
          getAccessTokenSilently,
        );
      } else if (field === "public_ind") {
        await updateUserProfile(
          { public_ind: value } as Partial<UserProfile>,
          getAccessTokenSilently,
        );
      } else {
        await updateUserProfile(
          { [field]: value } as Partial<UserProfile>,
          getAccessTokenSilently,
        );
      }
      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
      toast.success("Preference updated successfully");
    } catch (error) {
      console.error(`Failed to update ${field}:`, error);
      toast.error("Failed to update preference");
      throw error;
    }
  };

  const handleUIPrefsUpdate = async (key: string, value: boolean | string | string[]) => {
    try {
      await updateUserProfile(
        { ui_prefs: { [key]: value } } as unknown as Partial<UserProfile>,
        getAccessTokenSilently,
      );
      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
      toast.success("Preference updated successfully");
    } catch (error) {
      console.error(`Failed to update ui_prefs.${key}:`, error);
      toast.error("Failed to update preference");
      throw error; // Re-throw so callers can handle rollback
    }
  };

  // Get current categories from server state
  const currentCategories = user?.prefs?.ui_prefs?.default_categories ?? DEFAULT_CATEGORIES;

  const handleCategoryToggle = useCallback(async (categoryCode: string) => {
    const newCategories = currentCategories.includes(categoryCode)
      ? currentCategories.filter((c: string) => c !== categoryCode)
      : [...currentCategories, categoryCode];
    
    // Don't allow deselecting all categories
    if (newCategories.length === 0) {
      toast.error("You must have at least one category selected");
      return;
    }
    
    // Optimistically update the cache immediately
    const previousData = queryClient.getQueryData<UserProfile>(["user", "profile", "me"]);
    queryClient.setQueryData<UserProfile>(["user", "profile", "me"], (old) => {
      if (!old) return old;
      return {
        ...old,
        prefs: {
          ...old.prefs!,
          ui_prefs: {
            ...old.prefs?.ui_prefs,
            default_categories: newCategories,
          },
        },
      };
    });
    
    try {
      await updateUserProfile(
        { ui_prefs: { default_categories: newCategories } } as unknown as Partial<UserProfile>,
        getAccessTokenSilently,
      );
      // Success - no need to do anything, cache is already updated
    } catch (error) {
      // Rollback on failure by restoring previous data
      console.error("Failed to update default_categories:", error);
      toast.error("Failed to update preference");
      if (previousData) {
        queryClient.setQueryData(["user", "profile", "me"], previousData);
      }
    }
  }, [currentCategories, getAccessTokenSilently, queryClient]);

  if (isLoading) {
    return (
      <>
        <title>Preferences | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <div className="py-12 text-center">
            <Spinner size="lg" />
            <p className="text-gray-600 dark:text-gray-400 mt-4">Loading preferences...</p>
          </div>
        </div>
      </>
    );
  }

  if (error || !user || !user.prefs) {
    return (
      <>
        <title>Preferences | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 dark:text-red-400 text-lg">
                {error
                  ? "Failed to load preferences"
                  : "Preferences not available"}
              </p>
            </div>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <title>Preferences | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Preferences</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Customise your experience on Trigpointing.uk
          </p>
        </div>

        <Card className="mb-6">
          <div className="grid grid-cols-1 gap-6">
            {/* Default Trigpoint Categories */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Default Trigpoint Types
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Select which types of trigpoints to show by default on the map and browse pages.
                Click to toggle each type on or off.
              </p>
              <div className="flex flex-wrap gap-3">
                {TYPE_CATEGORIES.map((category) => {
                  const isSelected = currentCategories.includes(category.code);
                  return (
                    <button
                      key={category.code}
                      type="button"
                      onClick={() => handleCategoryToggle(category.code)}
                      className={`
                        inline-flex flex-col items-center justify-center
                        w-16 p-2 rounded-lg
                        transition-all duration-200
                        ${
                          isSelected
                            ? "bg-trig-green-600 shadow-md ring-2 ring-trig-green-400"
                            : "bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
                        }
                        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-trig-green-500
                      `}
                      title={`${category.name}: ${category.description}`}
                      aria-label={`${isSelected ? "Deselect" : "Select"} ${category.name}`}
                      aria-pressed={isSelected}
                    >
                      <img
                        src={category.icon}
                        alt={category.name}
                        className={`w-8 h-8 object-contain ${isSelected ? "" : "opacity-50"}`}
                      />
                      <span className={`text-xs mt-1 ${isSelected ? "text-white font-medium" : "text-gray-600 dark:text-gray-300"}`}>
                        {category.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Default Photo Licence Preference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Default Photo Licence
              </label>
              <select
                value={user.prefs?.public_ind || "N"}
                onChange={(e) =>
                  handleFieldUpdate("public_ind", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="N">Copyright me</option>
                <option value="Y">Public domain</option>
              </select>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Choose the default licence for photos you upload
              </p>
            </div>
          </div>
        </Card>

        {/* Display Options */}
        <Card className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Display Options
          </h2>
          <div className="space-y-6">
            {/* Distance Units Preference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Distance Units
              </label>
              <select
                value={user.prefs?.distance_ind || "K"}
                onChange={(e) =>
                  handleFieldUpdate("distance_ind", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="K">Kilometres (km)</option>
                <option value="M">Miles (mi)</option>
              </select>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Choose your preferred unit for displaying distances
              </p>
            </div>

            {/* Show Trig Condition */}
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="showTrigCondition"
                checked={user.prefs?.ui_prefs?.show_trig_condition ?? false}
                onChange={(e) =>
                  handleUIPrefsUpdate("show_trig_condition", e.target.checked)
                }
                className="mt-1 h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-trig-green-600 focus:ring-trig-green-500 dark:bg-gray-700"
              />
              <div>
                <label
                  htmlFor="showTrigCondition"
                  className="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer"
                >
                  Show curated trigpoint condition on log cards
                </label>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Display a condition icon before the trigpoint ID on log cards,
                  showing the current overall condition of the trigpoint.
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* Trigpoint Page Map Links */}
        <Card className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Trigpoint Page Map Links
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Choose which mapping service to open when clicking on coordinate
            links on trigpoint pages.
          </p>
          <div className="space-y-6">
            {/* OS Grid Reference Link */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                OS Grid Reference
              </label>
              <select
                value={
                  user.prefs?.ui_prefs?.map_link_gridref ??
                  MAP_LINK_DEFAULTS.gridref
                }
                onChange={(e) =>
                  handleUIPrefsUpdate(
                    "map_link_gridref",
                    e.target.value as MapLinkOption,
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500"
              >
                {MAP_LINK_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Opens when you click on the OS grid reference (e.g. TQ 30800
                79930)
              </p>
            </div>

            {/* WGS Coordinates Link */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                WGS Coordinates
              </label>
              <select
                value={
                  user.prefs?.ui_prefs?.map_link_wgs ?? MAP_LINK_DEFAULTS.wgs
                }
                onChange={(e) =>
                  handleUIPrefsUpdate(
                    "map_link_wgs",
                    e.target.value as MapLinkOption,
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500"
              >
                {MAP_LINK_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Opens when you click on the WGS84 coordinates (e.g. 51.50000,
                -0.12345)
              </p>
            </div>

            {/* Thumbnail Map Link */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Thumbnail Map
              </label>
              <select
                value={
                  user.prefs?.ui_prefs?.map_link_thumbnail ??
                  MAP_LINK_DEFAULTS.thumbnail
                }
                onChange={(e) =>
                  handleUIPrefsUpdate(
                    "map_link_thumbnail",
                    e.target.value as MapLinkOption,
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500"
              >
                {MAP_LINK_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Opens when you click on the small thumbnail map image on the
                trigpoint page
              </p>
            </div>
          </div>
        </Card>

        {/* Trig Lists */}
        {isAuthenticated && (
          <ListsPreferencesPanel hasAdminRole={hasAdminRole} />
        )}

        {/* Data Archive — admin-only until feature is ready for release */}
        {isAuthenticated && hasAdminRole && user && (
          <ArchivePreferencesPanel user={user} />
        )}
      </div>
    </>
  );
}
