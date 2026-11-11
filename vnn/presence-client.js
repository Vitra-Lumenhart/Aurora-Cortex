/* VNN browser consumer of aurora.broadcast/1.
 * Drop into EXISTING newsroom/studio markup; do not build a second portrait.
 * No privileged API, scheduler access, chat ingestion, or external URL.
 */
(function (global) {
  "use strict";

  function text(root, selector, value) {
    const node = root.querySelector(selector);
    if (node) node.textContent = String(value);
  }

  function validMedia(path) {
    return typeof path === "string"
      && path.startsWith("/news/media/")
      && /^\/news\/media\/[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(path)
      && path.split("/").every(part => part !== "." && part !== "..");
  }

  function fresh(manifest) {
    return manifest
      && manifest.schema === "aurora.broadcast/1"
      && manifest.surface === "news.vitra.ams"
      && Number.isFinite(Date.parse(manifest.stale_after))
      && Date.parse(manifest.stale_after) > Date.now();
  }

  function attach(options) {
    options = options || {};
    const root = options.root || document.querySelector("[data-vnn-studio]");
    if (!root) throw new Error("VNN needs a studio root (data-vnn-studio)");
    const endpoint = options.endpoint || "/news/api/broadcast-state.json";
    if (!endpoint.startsWith("/") || endpoint.startsWith("//")) {
      throw new Error("VNN state endpoint must be same-origin");
    }
    const pollMs = Math.max(3000, Number(options.pollMs) || 12000);
    let stopped = false;
    let lastVersion = "";
    let mediaPath = "";
    const video = root.querySelector("[data-vnn-video]");

    function down() {
      root.dataset.broadcastState = "unverified";
      root.dataset.broadcastFreshness = "stale";
      text(root, "[data-vnn-status]", "Broadcast state unavailable");
      text(root, "[data-vnn-title]", "The newsroom remains readable offline.");
      if (video) { video.pause(); video.removeAttribute("src"); video.load(); }
      mediaPath = "";
    }

    function apply(data) {
      if (!fresh(data)) { down(); return; }
      const state = data.state;
      root.dataset.broadcastFreshness = "fresh";
      root.dataset.broadcastState = state;
      text(root, "[data-vnn-status]", {
        presenting: "ON AIR · renderer acknowledged",
        cue_pending: "Preparing next segment",
        standby: "Studio standby",
        emergency: "Broadcast suspended"
      }[state] || "Studio status unknown");
      text(root, "[data-vnn-title]", data.program?.title || "VNN · Newsroom");
      const videoUrl = data.media?.video;
      // A still, no video, or an unacknowledged cue must not be called "live".
      if (video) {
        if (state === "presenting" && validMedia(videoUrl)) {
          if (mediaPath !== videoUrl) {
            video.pause();
            video.src = videoUrl;
            video.load();
            mediaPath = videoUrl;
          }
          video.hidden = false;
        } else {
          video.pause();
          video.removeAttribute("src");
          video.load();
          video.hidden = true;
          mediaPath = "";
        }
      }
      const face = data.face || {};
      // Vitra's existing Python/Canvas portrait owns pixels. This is only a
      // typed expression cue, not a separately-drawn imitation of her.
      if (face.gesture) {
        root.dataset.vitraGesture = String(face.gesture);
        const version = [data.generated_at, state, data.program?.segment_id, face.gesture,
          face.amplitude, face.tempo, face.restraint].join("|");
        if (lastVersion !== version) {
          lastVersion = version;
          root.dispatchEvent(new CustomEvent("vitra:expression", {
            bubbles: true, detail: {
              gesture: face.gesture, amplitude: face.amplitude,
              tempo: face.tempo, restraint: face.restraint,
              source: face.source || "unknown", broadcastState: state
            }
          }));
        }
      }
    }

    async function refresh() {
      if (stopped) return;
      try {
        const response = await fetch(endpoint, {
          cache: "no-store", credentials: "same-origin",
          headers: { Accept: "application/json" }
        });
        if (!response.ok) throw new Error("state unavailable");
        apply(await response.json());
      } catch (_error) { down(); }
    }

    // Not a claim of transport: network events are read-only; no auto-play.
    // Visitors may explicitly click the existing playback button when ready.
    refresh();
    const handle = global.setInterval(refresh, pollMs);
    return {
      refresh: refresh,
      stop: function () {
        stopped = true;
        global.clearInterval(handle);
      }
    };
  }

  global.VNNPresence = Object.freeze({ attach: attach });
})(window);
