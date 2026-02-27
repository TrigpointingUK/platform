import { useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";

const AUTH0_ANDROID_DOMAIN = "auth.trigpointing.uk";
const DEFAULT_ANDROID_PACKAGE = "uk.trigpointing.android";
const ANDROID_CALLBACK_PATH_RE = /^\/android\/(uk\.trigpointing\.android(?:\.debug)?)\/callback$/;

function getAndroidPackageFromPath(pathname: string): string {
  const match = ANDROID_CALLBACK_PATH_RE.exec(pathname);
  return match?.[1] ?? DEFAULT_ANDROID_PACKAGE;
}

function buildAndroidDeepLink(pathname: string, search: string, hash: string): string {
  const packageName = getAndroidPackageFromPath(pathname);
  return `${packageName}://${AUTH0_ANDROID_DOMAIN}/android/${packageName}/callback${search}${hash}`;
}

function setHeadMeta(attributeName: "name" | "http-equiv", attributeValue: string, content: string): void {
  const selector = `meta[${attributeName}="${attributeValue}"]`;
  let metaTag = document.head.querySelector(selector) as HTMLMetaElement | null;

  if (!metaTag) {
    metaTag = document.createElement("meta");
    metaTag.setAttribute(attributeName, attributeValue);
    document.head.appendChild(metaTag);
  }

  metaTag.setAttribute("content", content);
}

export default function AndroidAuthCallback() {
  const location = useLocation();

  const callbackError = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("error");
  }, [location.search]);

  const deepLink = useMemo(
    () => buildAndroidDeepLink(location.pathname, location.search, location.hash),
    [location.hash, location.pathname, location.search]
  );

  useEffect(() => {
    document.title = "Open TrigpointingUK App";
    setHeadMeta("name", "robots", "noindex, nofollow, noarchive");
    setHeadMeta("http-equiv", "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
    setHeadMeta("http-equiv", "Pragma", "no-cache");
    setHeadMeta("http-equiv", "Expires", "0");
  }, []);

  useEffect(() => {
    if (import.meta.env.MODE === "test") {
      return;
    }

    const openTimer = window.setTimeout(() => {
      window.location.assign(deepLink);
    }, 150);

    return () => {
      window.clearTimeout(openTimer);
    };
  }, [deepLink]);

  return (
    <div className="min-h-dvh bg-gray-50 px-4 py-10 text-gray-900 dark:bg-gray-900 dark:text-gray-100">
      <main className="mx-auto w-full max-w-lg rounded-xl border border-gray-200 bg-white p-6 shadow-lg dark:border-gray-700 dark:bg-gray-800">
        <img className="mx-auto mb-4 h-14 w-14" src="/TUK-Logo.svg" alt="TrigpointingUK logo" />
        <h1 className="mb-3 text-center text-2xl font-bold">Continue in the TrigpointingUK app</h1>

        {callbackError ? (
          <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-200">
            We could not complete sign-in in the app. Please return to login and try again.
          </p>
        ) : (
          <p className="mb-4 text-sm text-gray-700 dark:text-gray-300">
            We are trying to open the app automatically.
          </p>
        )}

        <a
          href={deepLink}
          rel="nofollow"
          className="mb-4 inline-flex w-full items-center justify-center rounded-md bg-trig-green-600 px-4 py-3 text-center font-semibold text-white transition-colors hover:bg-trig-green-500 focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:ring-offset-2"
        >
          Open TrigpointingUK App
        </a>

        <p className="mb-2 text-sm text-gray-700 dark:text-gray-300">If the app does not open:</p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-300">
          <li>Tap the button above.</li>
          <li>Enable "Open supported links" for TrigpointingUK in Android settings.</li>
          <li>Update the app to the latest version, then retry login.</li>
        </ul>
      </main>
    </div>
  );
}
