(() => {
  "use strict";

  const VIDEOJS_CSS_URL = "https://vjs.zencdn.net/8.16.1/video-js.css";
  const VIDEOJS_JS_URL = "https://vjs.zencdn.net/8.16.1/video.min.js";
  const QUALITY_LEVELS_JS_URL =
    "https://cdn.jsdelivr.net/npm/videojs-contrib-quality-levels@4.1.0/dist/videojs-contrib-quality-levels.min.js";
  const QUALITY_SELECTOR_CSS_URL =
    "https://cdn.jsdelivr.net/npm/videojs-quality-selector-hls@1.1.1/dist/videojs-quality-selector-hls.css";
  const QUALITY_SELECTOR_JS_URL =
    "https://cdn.jsdelivr.net/npm/videojs-quality-selector-hls@1.1.1/dist/videojs-quality-selector-hls.min.js";

  function onDocumentReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
      return;
    }
    callback();
  }

  function ensureStylesheet(href, id) {
    if (document.getElementById(id)) {
      return;
    }
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }

  function ensureScript(src, id, onLoad) {
    const existing = document.getElementById(id);
    if (existing) {
      const readyState = existing.readyState || "";
      if (existing.dataset.loaded === "1" || readyState === "loaded" || readyState === "complete") {
        onLoad();
      } else {
        existing.addEventListener("load", onLoad, { once: true });
      }
      return;
    }

    const script = document.createElement("script");
    script.id = id;
    script.src = src;
    script.defer = true;
    script.addEventListener(
      "load",
      () => {
        script.dataset.loaded = "1";
        onLoad();
      },
      { once: true }
    );
    document.head.appendChild(script);
  }

  function buildPlayer(target) {
    if (target.dataset.trigPlayerInitialised === "1") {
      return;
    }

    const hlsSrc = target.getAttribute("data-hls-src");
    if (!hlsSrc) {
      return;
    }

    const posterSrc = target.getAttribute("data-poster") || "";
    const video = document.createElement("video");
    video.className = "video-js vjs-default-skin vjs-big-play-centered";
    video.setAttribute("controls", "");
    video.setAttribute("playsinline", "");
    video.setAttribute("preload", "metadata");
    video.setAttribute("disablePictureInPicture", "");
    video.disablePictureInPicture = true;
    video.muted = true;
    video.loop = true;
    if (posterSrc) {
      video.setAttribute("poster", posterSrc);
    }

    const source = document.createElement("source");
    source.src = hlsSrc;
    source.type = "application/x-mpegURL";
    video.appendChild(source);

    target.appendChild(video);
    const player = window.videojs(video, {
      autoplay: "muted",
      controls: true,
      fluid: true,
      responsive: true,
      preload: "metadata",
      muted: true,
      loop: true,
      disablePictureInPicture: true,
      enableDocumentPictureInPicture: false,
      html5: {
        vhs: {
          overrideNative: true,
        },
      },
      controlBar: {
        pictureInPictureToggle: false,
      },
    });

    if (typeof player.qualitySelectorHls === "function") {
      player.qualitySelectorHls({
        displayCurrentQuality: true,
        vjsIconClass: "vjs-icon-hd",
      });
    }

    target.dataset.trigPlayerInitialised = "1";
  }

  function initHomeVideo() {
    const targets = document.querySelectorAll(".trig-home-video[data-hls-src]");
    if (!targets.length) {
      return;
    }

    ensureStylesheet(VIDEOJS_CSS_URL, "trig-videojs-cdn-css");
    ensureStylesheet(QUALITY_SELECTOR_CSS_URL, "trig-videojs-quality-selector-css");

    ensureScript(VIDEOJS_JS_URL, "trig-videojs-cdn-js", () => {
      ensureScript(QUALITY_LEVELS_JS_URL, "trig-videojs-quality-levels-js", () => {
        ensureScript(QUALITY_SELECTOR_JS_URL, "trig-videojs-quality-selector-js", () => {
          targets.forEach((target) => buildPlayer(target));
        });
      });
    });
  }

  onDocumentReady(initHomeVideo);
})();
