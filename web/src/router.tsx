import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider, Navigate, useParams } from "react-router-dom";
import Spinner from "./components/ui/Spinner";
// NotFound is eagerly loaded to ensure it's always available, even if there are deployment issues
import NotFound from "./routes/NotFound";

const Home = lazy(() => import("./routes/Home"));
const Logs = lazy(() => import("./routes/Logs"));
const PhotoAlbum = lazy(() => import("./routes/PhotoAlbum"));
const PhotoDetail = lazy(() => import("./routes/PhotoDetail"));
const TrigDetail = lazy(() => import("./routes/TrigDetail"));
const TrigPhotos = lazy(() => import("./routes/TrigPhotos"));
const LogDetail = lazy(() => import("./routes/LogDetail"));
const UserProfile = lazy(() => import("./routes/UserProfile"));
const UserLogs = lazy(() => import("./routes/UserLogs"));
const UserPhotos = lazy(() => import("./routes/UserPhotos"));
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
const AdminTrigEdit = lazy(() => import("./routes/admin/TrigEdit"));

// Redirect component for old /trig/ URLs
function TrigRedirect() {
  const { trigId } = useParams();
  return <Navigate to={`/trigs/${trigId}`} replace />;
}

function TrigPhotosRedirect() {
  const { trigId } = useParams();
  return <Navigate to={`/trigs/${trigId}/photos`} replace />;
}

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <Spinner size="lg" />
        <p className="mt-4 text-gray-600">Loading...</p>
      </div>
    </div>
  );
}

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <Home />
        </Suspense>
      ),
    },
    {
      path: "/logs",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <Logs />
        </Suspense>
      ),
    },
      {
        path: "/trigs",
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <FindTrigs />
          </Suspense>
        ),
      },
      {
        path: "/map",
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <Map />
          </Suspense>
        ),
      },
      {
        path: "/search",
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <Search />
          </Suspense>
        ),
      },
    {
      path: "/logs/:logId",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <LogDetail />
        </Suspense>
      ),
    },
    {
      path: "/photos",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <PhotoAlbum />
        </Suspense>
      ),
    },
    {
      path: "/photos/:photo_id",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <PhotoDetail />
        </Suspense>
      ),
    },
    // Redirect old /trig/ URLs to /trigs/ for backwards compatibility
    {
      path: "/trig/:trigId",
      element: <TrigRedirect />,
    },
    {
      path: "/trig/:trigId/photos",
      element: <TrigPhotosRedirect />,
    },
    // New canonical /trigs/ routes
    {
      path: "/trigs/:trigId",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <TrigDetail />
        </Suspense>
      ),
    },
    {
      path: "/trigs/:trigId/photos",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <TrigPhotos />
        </Suspense>
      ),
    },
    {
      path: "/profile/:userId",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <UserProfile />
        </Suspense>
      ),
    },
    {
      path: "/profile/:userId/logs",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <UserLogs />
        </Suspense>
      ),
    },
    {
      path: "/profile/:userId/photos",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <UserPhotos />
        </Suspense>
      ),
    },
    {
      path: "/profile",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <UserProfile />
        </Suspense>
      ),
    },
    {
      path: "/about",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <About />
        </Suspense>
      ),
    },
    {
      path: "/app/:id",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <AppDetail />
        </Suspense>
      ),
    },
    {
      path: "/legacy-migration",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <LegacyMigration />
        </Suspense>
      ),
    },
    {
      path: "/contact",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <Contact />
        </Suspense>
      ),
    },
    {
      path: "/attributions",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <Attributions />
        </Suspense>
      ),
    },
    {
      path: "/admin",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <Admin />
        </Suspense>
      ),
    },
    {
      path: "/admin/needs-attention",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <AdminNeedsAttention />
        </Suspense>
      ),
    },
    {
      path: "/admin/trigs/:trigId/edit",
      element: (
        <Suspense fallback={<LoadingFallback />}>
          <AdminTrigEdit />
        </Suspense>
      ),
    },
    {
      path: "*",
      element: <NotFound />,
    },
  ],
  {
    basename: import.meta.env.BASE_URL,
  }
);

export default function AppRouter() {
  return <RouterProvider router={router} />;
}
