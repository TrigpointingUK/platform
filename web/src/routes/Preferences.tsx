import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import {
  useUserProfile,
  updateUserProfile,
  type UserProfile,
  type MapLinkOption,
} from "../hooks/useUserProfile";
import { MAP_LINK_OPTIONS, MAP_LINK_DEFAULTS } from "../lib/mapLinks";

// Trigpoint type groups - matches trig_type_group table
const TYPE_GROUPS = [
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

// Default groups for new users (Pillar, FBM, Survey mark)
const DEFAULT_GROUPS = ["PILLAR", "FBM", "SURVEY_MARK"];

export default function Preferences() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();

  // Fetch current user's profile with preferences
  const { data: user, isLoading, error } = useUserProfile("me");

  const handleFieldUpdate = async (field: string, value: string) => {
    try {
      if (field === "status_max") {
        // Parse status_max as an integer
        await updateUserProfile(
          { status_max: parseInt(value, 10) } as Partial<UserProfile>,
          getAccessTokenSilently,
        );
      } else if (field === "distance_ind") {
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

  // Get current groups from server state
  const currentGroups = user?.prefs?.ui_prefs?.default_groups ?? DEFAULT_GROUPS;

  const handleGroupToggle = useCallback(async (groupCode: string) => {
    const newGroups = currentGroups.includes(groupCode)
      ? currentGroups.filter((g: string) => g !== groupCode)
      : [...currentGroups, groupCode];
    
    // Don't allow deselecting all groups
    if (newGroups.length === 0) {
      toast.error("You must have at least one group selected");
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
            default_groups: newGroups,
          },
        },
      };
    });
    
    try {
      await updateUserProfile(
        { ui_prefs: { default_groups: newGroups } } as unknown as Partial<UserProfile>,
        getAccessTokenSilently,
      );
      // Success - no need to do anything, cache is already updated
    } catch (error) {
      // Rollback on failure by restoring previous data
      console.error("Failed to update default_groups:", error);
      toast.error("Failed to update preference");
      if (previousData) {
        queryClient.setQueryData(["user", "profile", "me"], previousData);
      }
    }
  }, [currentGroups, getAccessTokenSilently, queryClient]);

  if (isLoading) {
    return (
      <Layout>
        <title>Preferences | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <div className="py-12 text-center">
            <Spinner size="lg" />
            <p className="text-gray-600 mt-4">Loading preferences...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !user || !user.prefs) {
    return (
      <Layout>
        <title>Preferences | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 text-lg">
                {error
                  ? "Failed to load preferences"
                  : "Preferences not available"}
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <title>Preferences | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Preferences</h1>
          <p className="text-gray-600">
            Customise your experience on Trigpointing.uk
          </p>
        </div>

        <Card className="mb-6">
          <div className="grid grid-cols-1 gap-6">
            {/* Default Trigpoint Groups */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Default Trigpoint Types
              </label>
              <p className="text-xs text-gray-500 mb-3">
                Select which types of trigpoints to show by default on the map and browse pages.
                Click to toggle each type on or off.
              </p>
              <div className="flex flex-wrap gap-3">
                {TYPE_GROUPS.map((group) => {
                  const isSelected = currentGroups.includes(group.code);
                  return (
                    <button
                      key={group.code}
                      type="button"
                      onClick={() => handleGroupToggle(group.code)}
                      className={`
                        inline-flex flex-col items-center justify-center
                        w-16 p-2 rounded-lg
                        transition-all duration-200
                        ${
                          isSelected
                            ? "bg-trig-green-600 shadow-md ring-2 ring-trig-green-400"
                            : "bg-gray-100 hover:bg-gray-200"
                        }
                        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-trig-green-500
                      `}
                      title={`${group.name}: ${group.description}`}
                      aria-label={`${isSelected ? "Deselect" : "Select"} ${group.name}`}
                      aria-pressed={isSelected}
                    >
                      <img
                        src={group.icon}
                        alt={group.name}
                        className={`w-8 h-8 object-contain ${isSelected ? "" : "opacity-50"}`}
                      />
                      <span className={`text-xs mt-1 ${isSelected ? "text-white font-medium" : "text-gray-600"}`}>
                        {group.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Default Photo Licence Preference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Default Photo Licence
              </label>
              <select
                value={user.prefs?.public_ind || "N"}
                onChange={(e) =>
                  handleFieldUpdate("public_ind", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="N">Copyright me</option>
                <option value="Y">Public domain</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
                Choose the default licence for photos you upload
              </p>
            </div>
          </div>
        </Card>

        {/* Display Options */}
        <Card className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Display Options
          </h2>
          <div className="space-y-6">
            {/* Distance Units Preference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Distance Units
              </label>
              <select
                value={user.prefs?.distance_ind || "K"}
                onChange={(e) =>
                  handleFieldUpdate("distance_ind", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="K">Kilometres (km)</option>
                <option value="M">Miles (mi)</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
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
                className="mt-1 h-4 w-4 rounded border-gray-300 text-trig-green-600 focus:ring-trig-green-500"
              />
              <div>
                <label
                  htmlFor="showTrigCondition"
                  className="text-sm font-medium text-gray-700 cursor-pointer"
                >
                  Show curated trigpoint condition on log cards
                </label>
                <p className="text-xs text-gray-500 mt-1">
                  Display a condition icon before the trigpoint ID on log cards,
                  showing the current overall condition of the trigpoint.
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* Trigpoint Page Map Links */}
        <Card className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Trigpoint Page Map Links
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Choose which mapping service to open when clicking on coordinate
            links on trigpoint pages.
          </p>
          <div className="space-y-6">
            {/* OS Grid Reference Link */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                {MAP_LINK_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500">
                Opens when you click on the OS grid reference (e.g. TQ 30800
                79930)
              </p>
            </div>

            {/* WGS Coordinates Link */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                {MAP_LINK_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500">
                Opens when you click on the WGS84 coordinates (e.g. 51.50000,
                -0.12345)
              </p>
            </div>

            {/* Thumbnail Map Link */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                {MAP_LINK_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500">
                Opens when you click on the small thumbnail map image on the
                trigpoint page
              </p>
            </div>
          </div>
        </Card>
      </div>
    </Layout>
  );
}
