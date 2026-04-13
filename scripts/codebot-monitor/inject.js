/**
 * Codebot monitor – paste this in the Codebot builder page console while the monitor server is running.
 * Sends your inputs (prompt paste, build click) and API traffic (builder/run, etc.) to the monitor.
 */
(function () {
  const MONITOR_URL = "MONITOR_URL_PLACEHOLDER"; // replaced by server
  if (typeof MONITOR_URL === "string" && !MONITOR_URL.startsWith("http")) return;

  function send(evt) {
    try {
      fetch(MONITOR_URL + "/event", {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ts: Date.now(), ...evt }),
      }).catch(() => {});
    } catch (_) {}
  }

  // --- Intercept fetch (Codebot API calls) ---
  const origFetch = window.fetch;
  window.fetch = function (url, opts) {
    const urlStr = typeof url === "string" ? url : (url && url.url) || "";
    const isCodebot =
      /builder\/run|builder\/npm-install|projects\/from-files|projects\/\w+\/export|auth\/whoami|auth\/session|\/me\b/.test(
        urlStr
      );
    const start = Date.now();
    const method = (opts && opts.method) || "GET";

    if (isCodebot) {
      send({
        source: "frontend",
        type: "fetch_start",
        method,
        url: urlStr.split("?")[0],
      });
    }

    return origFetch.apply(this, arguments).then(
      (res) => {
        if (isCodebot) {
          send({
            source: "frontend",
            type: "fetch_end",
            method,
            url: urlStr.split("?")[0],
            status: res.status,
            ok: res.ok,
            ms: Date.now() - start,
          });
        }
        return res;
      },
      (err) => {
        if (isCodebot) {
          send({
            source: "frontend",
            type: "fetch_error",
            method,
            url: urlStr.split("?")[0],
            error: (err && err.message) || String(err),
            ms: Date.now() - start,
          });
        }
        throw err;
      }
    );
  };

  // --- Builder prompt & build button ---
  function attachBuilder() {
    const textarea = document.querySelector('[data-testid="builder-prompt"]');
    const buildBtn = document.querySelector('[data-testid="builder-build-now"]');

    if (textarea && !textarea.dataset.monitorAttached) {
      textarea.dataset.monitorAttached = "1";
      textarea.addEventListener("paste", function (e) {
        setTimeout(() => {
          const v = (textarea.value || "").trim();
          send({
            source: "user",
            type: "prompt_paste",
            length: v.length,
            preview: v.slice(0, 300),
          });
        }, 0);
      });
      textarea.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
          send({
            source: "user",
            type: "prompt_submit",
            length: (textarea.value || "").trim().length,
          });
        }
      });
    }

    if (buildBtn && !buildBtn.dataset.monitorAttached) {
      buildBtn.dataset.monitorAttached = "1";
      buildBtn.addEventListener("click", function () {
        const v = (document.querySelector('[data-testid="builder-prompt"]')?.value || "").trim();
        send({
          source: "user",
          type: "build_click",
          promptLength: v.length,
          preview: v.slice(0, 300),
        });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attachBuilder);
  } else {
    attachBuilder();
  }
  setInterval(attachBuilder, 1500);

  send({ source: "frontend", type: "monitor_attached", url: location.href });
  console.log("[Codebot monitor] Attached. Events are being sent to " + MONITOR_URL);
})();
