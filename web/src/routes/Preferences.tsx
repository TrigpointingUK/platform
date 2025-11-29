import { useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import { useUserProfile, updateUserProfile, type UserProfile } from "../hooks/useUserProfile";

export default function Preferences() {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently } = useAuth0();
  
  // Fetch current user's profile with preferences
  const { data: user, isLoading, error } = useUserProfile("me");

  const handleFieldUpdate = async (field: string, value: string) => {
    try {
      if (field === "status_max") {
        // Parse status_max as an integer
        await updateUserProfile({ status_max: parseInt(value, 10) } as Partial<UserProfile>, getAccessTokenSilently);
      } else if (field === "distance_ind") {
        await updateUserProfile({ distance_ind: value } as Partial<UserProfile>, getAccessTokenSilently);
      } else if (field === "public_ind") {
        await updateUserProfile({ public_ind: value } as Partial<UserProfile>, getAccessTokenSilently);
      } else {
        await updateUserProfile({ [field]: value } as Partial<UserProfile>, getAccessTokenSilently);
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

  if (isLoading) {
    return (
      <Layout>
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
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 text-lg">
                {error ? "Failed to load preferences" : "Preferences not available"}
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Preferences
          </h1>
          <p className="text-gray-600">
            Customise your experience on Trigpointing.uk
          </p>
        </div>

        {/* Visibility Preferences */}
        <Card className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Visibility Preferences
          </h2>
          <div className="grid grid-cols-1 gap-6">
            {/* Status Max Preference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Maximum Status Level
              </label>
              <select
                value={user.prefs.status_max || 30}
                onChange={(e) => handleFieldUpdate("status_max", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="10">Pillar only</option>
                <option value="20">Major marks (Pillars, FBMs, Curry Stools)</option>
                <option value="30">Minor marks (includes Bolts, Blocks)</option>
                <option value="40">Intersected (includes Intersected stations)</option>
                <option value="50">User Added (includes user-submitted)</option>
                <option value="60">Controversial (includes Irish, benchmarks, oddities)</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
                Controls which trigpoints you see on the map and browse pages. Higher levels include all lower levels.
              </p>
            </div>

            {/* Distance Units Preference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Distance Units
              </label>
              <select
                value={user.prefs?.distance_ind || "K"}
                onChange={(e) => handleFieldUpdate("distance_ind", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="K">Kilometres (km)</option>
                <option value="M">Miles (mi)</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
                Choose your preferred unit for displaying distances
              </p>
            </div>
          </div>
        </Card>

        {/* Privacy Preferences */}
        <Card className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Privacy Preferences
          </h2>
          <div className="grid grid-cols-1 gap-6">
            {/* Public Profile */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Public Profile
              </label>
              <select
                value={user.prefs?.public_ind || "N"}
                onChange={(e) => handleFieldUpdate("public_ind", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="Y">Public - visible to everyone</option>
                <option value="N">Private - visible only to you</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
                Controls whether other users can view your profile
              </p>
            </div>
          </div>
        </Card>
      </div>
    </Layout>
  );
}

