(() => {
  "use strict";

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
      if (window.videojs) {
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
    script.addEventListener("load", onLoad, { once: true });
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
    window.videojs(video, {
      autoplay: "muted",
      controls: true,
      fluid: true,
      responsive: true,
      preload: "metadata",
      muted: true,
      loop: true,
    });

    target.dataset.trigPlayerInitialised = "1";
  }

  function initHomeVideo() {
    const targets = document.querySelectorAll(".trig-home-video[data-hls-src]");
    if (!targets.length) {
      return;
    }

    ensureStylesheet(
      "https://vjs.zencdn.net/8.16.1/video-js.css",
      "trig-videojs-cdn-css"
    );
    ensureScript(
      "https://vjs.zencdn.net/8.16.1/video.min.js",
      "trig-videojs-cdn-js",
      () => {
        targets.forEach((target) => buildPlayer(target));
      }
    );
  }

  onDocumentReady(initHomeVideo);
})();
