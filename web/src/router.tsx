import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider, Navigate, Outlet, useParams } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Spinner from "./components/ui/Spinner";
// NotFound is eagerly loaded to ensure it's always available, even if there are deployment issues
import NotFound from "./routes/NotFound";

// High-traffic routes loaded eagerly to eliminate the lazy-chunk round-trip for
// pages that are the most common search-engine entry points.
import Home from "./routes/Home";
import TrigDetail from "./routes/TrigDetail";
import LogDetail from "./routes/LogDetail";

const Logs = lazy(() => import("./routes/Logs"));
const PhotoAlbum = lazy(() => import("./routes/PhotoAlbum"));
const PhotoDetail = lazy(() => import("./routes/PhotoDetail"));
const TrigPhotos = lazy(() => import("./routes/TrigPhotos"));
const UsersPage = lazy(() => import("./routes/UsersPage"));
const UserProfile = lazy(() => import("./routes/UserProfile"));
const UserPhotos = lazy(() => import("./routes/UserPhotos"));
const Preferences = lazy(() => import("./routes/Preferences"));
const About = lazy(() => import("./routes/About"));
const AppDetail = lazy(() => import("./routes/AppDetail"));
const FindTrigs = lazy(() => import("./routes/FindTrigs"));
const Map = lazy(() => import("./routes/Map"));
const Search = lazy(() => import("./routes/Search"));
const LegacyMigration = lazy(() => import("./routes/LegacyMigration"));
const Contact = lazy(() => import("./routes/Contact"));
const Attributions = lazy(() => import("./routes/Attributions"));
const Admin = lazy(() => import("./routes/Admin"));
const AdminNeedsAttention = lazy(() => import("./routes/admin/NeedsAttention"));
const AdminLogsNeedsAttention = lazy(() => import("./routes/admin/LogsNeedsAttention"));
const AdminTrigEdit = lazy(() => import("./routes/admin/TrigEdit"));
const AdminTrigCreate = lazy(() => import("./routes/admin/TrigCreate"));
const AdminTypesAdmin = lazy(() => import("./routes/admin/TypesAdmin"));
const AdminStatusAdmin = lazy(() => import("./routes/admin/StatusAdmin"));
const AdminConditionAdmin = lazy(() => import("./routes/admin/ConditionAdmin"));
const AdminOSNetComparison = lazy(() => import("./routes/admin/OSNetComparison"));
const AdminIrelandImport = lazy(() => import("./routes/admin/IrelandImport"));
const SurveyTimeline = lazy(() => import("./routes/SurveyTimeline"));
const TrigLists = lazy(() => import("./routes/TrigLists"));
const Experiments = lazy(() => import("./routes/Experiments"));
const ExperimentIndex = lazy(() => import("./routes/ExperimentIndex"));
const TrigsV2 = lazy(() => import("./routes/experiment/TrigsV2"));
const TrigModel = lazy(() => import("./routes/experiment/TrigModel"));
const Coop = lazy(() => import("./routes/experiment/Coop"));
const AndroidAuthCallback = lazy(() => import("./routes/AndroidAuthCallback"));

// Redirect component for old /trig/ URLs
function TrigRedirect() {
  const { trigId } = useParams();
  return <Navigate to={`/trigs/${trigId}`} replace />;
}

function TrigPhotosRedirect() {
  const { trigId } = useParams();
  return <Navigate to={`/trigs/${trigId}/photos`} replace />;
}

function UserLogsRedirect() {
  const { userId } = useParams();
  return <Navigate to={`/logs?user=${userId}`} replace />;
}

/**
 * Fallback shown in the content area while a lazy route chunk loads.
 * Renders inside the already-visible Layout (header + footer stay painted),
 * so the only visual change is in the main content area -- avoiding CLS.
 */
function ContentFallback() {
  return (
    <div className="flex items-center justify-center py-24">
      <div className="text-center">
        <Spinner size="lg" />
        <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
      </div>
    </div>
  );
}

/**
 * Full-viewport fallback for routes that render their own layout
 * (Search, AndroidAuthCallback) and don't sit inside the shared Layout.
 */
function FullPageFallback() {
  return (
    <div className="flex items-center justify-center min-h-dvh bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <Spinner size="lg" />
        <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
      </div>
    </div>
  );
}

/**
 * Root layout route: renders the shared Header + Footer eagerly, and wraps the
 * child route's <Outlet /> in Suspense so the page chrome is always visible.
 */
function LayoutRoute() {
  return (
    <Layout>
      <Suspense fallback={<ContentFallback />}>
        <Outlet />
      </Suspense>
    </Layout>
  );
}

const router = createBrowserRouter(
  [
    // Routes that use the shared Layout (Header + content + Footer)
    {
      element: <LayoutRoute />,
      children: [
        { path: "/", element: <Home /> },
        { path: "/logs", element: <Logs /> },
        { path: "/users", element: <UsersPage /> },
        { path: "/trigs", element: <FindTrigs /> },
        { path: "/map", element: <Map /> },
        { path: "/logs/:logId", element: <LogDetail /> },
        { path: "/photos", element: <PhotoAlbum /> },
        { path: "/photos/:photo_id", element: <PhotoDetail /> },
        // Redirect old /trig/ URLs to /trigs/ for backwards compatibility
        { path: "/trig/:trigId", element: <TrigRedirect /> },
        { path: "/trig/:trigId/photos", element: <TrigPhotosRedirect /> },
        // New canonical /trigs/ routes
        { path: "/trigs/:trigId", element: <TrigDetail /> },
        { path: "/trigs/:trigId/photos", element: <TrigPhotos /> },
        { path: "/profile/:userId", element: <UserProfile /> },
        { path: "/profile/:userId/logs", element: <UserLogsRedirect /> },
        { path: "/profile/:userId/photos", element: <UserPhotos /> },
        { path: "/profile", element: <UserProfile /> },
        { path: "/preferences", element: <Preferences /> },
        { path: "/lists", element: <TrigLists /> },
        { path: "/lists/:listId", element: <TrigLists /> },
        { path: "/settings", element: <Navigate to="/preferences" replace /> },
        { path: "/about", element: <About /> },
        { path: "/app/:id", element: <AppDetail /> },
        { path: "/legacy-migration", element: <LegacyMigration /> },
        { path: "/contact", element: <Contact /> },
        { path: "/attributions", element: <Attributions /> },
        // Experimental routes
        { path: "/experiment", element: <ExperimentIndex /> },
        { path: "/experiment/survey-timeline", element: <SurveyTimeline /> },
        { path: "/experiment/coordinates", element: <Experiments /> },
        { path: "/experiment/trigs-v2", element: <TrigsV2 /> },
        { path: "/experiment/3d-model", element: <TrigModel /> },
        { path: "/experiment/coop", element: <Coop /> },
        // Admin routes
        { path: "/admin", element: <Admin /> },
        { path: "/admin/needs-attention", element: <AdminNeedsAttention /> },
        { path: "/admin/attention/logs", element: <AdminLogsNeedsAttention /> },
        { path: "/admin/trigs/new", element: <AdminTrigCreate /> },
        { path: "/admin/trigs/:trigId/edit", element: <AdminTrigEdit /> },
        { path: "/admin/types", element: <AdminTypesAdmin /> },
        { path: "/admin/status", element: <AdminStatusAdmin /> },
        { path: "/admin/condition", element: <AdminConditionAdmin /> },
        { path: "/admin/osnet", element: <AdminOSNetComparison /> },
        { path: "/admin/ireland-import", element: <AdminIrelandImport /> },
        { path: "*", element: <NotFound /> },
      ],
    },
    // Routes that render their own layout (no shared Header/Footer)
    {
      path: "/search",
      element: (
        <Suspense fallback={<FullPageFallback />}>
          <Search />
        </Suspense>
      ),
    },
    {
      path: "/android/uk.trigpointing.android/callback",
      element: (
        <Suspense fallback={<FullPageFallback />}>
          <AndroidAuthCallback />
        </Suspense>
      ),
    },
    {
      path: "/android/uk.trigpointing.android.debug/callback",
      element: (
        <Suspense fallback={<FullPageFallback />}>
          <AndroidAuthCallback />
        </Suspense>
      ),
    },
  ],
  {
    basename: import.meta.env.BASE_URL,
  }
);

export default function AppRouter() {
  return <RouterProvider router={router} />;
}
