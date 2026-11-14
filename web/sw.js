/* NYAYMITRA 2.0 — Service Worker
 *
 * Provides offline fallback for the app shell. API calls are NOT cached
 * (they may contain personal data), so the app degrades gracefully offline.
 */

const CACHE_NAME = "nyaymitra-v3";   // bump whenever the app shell changes (cache-first)
const APP_SHELL = [
  "/",
  "/config.js",
  "/app.js",
  "/locales/index.json",
  "/locales/en.json",
  "/locales/gu.json",
  "/styles.css",
  "/manifest.webmanifest",
  "/favicon.svg",
];

const APP_SHELL_ICONS = [
  "/assets/icons/icon-72x72.png",
  "/assets/icons/icon-96x96.png",
  "/assets/icons/icon-128x128.png",
  "/assets/icons/icon-144x144.png",
  "/assets/icons/icon-152x152.png",
  "/assets/icons/icon-192x192.png",
  "/assets/icons/icon-192x192-maskable.png",
  "/assets/icons/icon-384x384.png",
  "/assets/icons/icon-512x512.png",
  "/assets/icons/icon-512x512-maskable.png",
];

const OFFLINE_HTML = [
  "<!DOCTYPE html>",
  "<html lang='gu'>",
  "<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
  "<title>NYAYMITRA 2.0 — Offline</title>",
  "<style>",
  "body{font-family:sans-serif;background:#070c18;color:#e8e8e8;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;padding:20px;text-align:center}",
  "h1{color:#e8c96a;margin-bottom:12px}",
  "p{color:#b8c4d6;line-height:1.5;max-width:400px}",
  ".btn{margin-top:16px;padding:10px 20px;background:#e8c96a;color:#070c18;border:none;border-radius:6px;cursor:pointer;text-decoration:none;display:inline-block;font-weight:bold}",
  "</style>",
  "</head>",
  "<body>",
  "<h1>NYAYMITRA 2.0</h1>",
  "<p>આપણે હાલ ઓફલાઇન છીએ. સંગ્રહિત પેજો જોઈ શકો છો, પણ નવું સર્વર સંપર્ક કરવો શક્ય નથી.</p>",
  "<p>We are currently offline. Cached pages remain available, but new server requests cannot be made.</p>",
  "<a class='btn' href='/'>ફરીથી પ્રયાસ કરો / Try again</a>",
  "</body>",
  "</html>",
].join("");

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([...APP_SHELL, ...APP_SHELL_ICONS]);
    }),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)),
      );
    }),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin GET requests
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // API routes: try network first, then fail gracefully (no caching of personal data)
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({
            code: "offline",
            message: "You are offline. This request cannot be completed without a server connection.",
          }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        );
      }),
    );
    return;
  }

  // App shell: cache-first, then network
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request).then((response) => {
        // Other interface catalogues are cached the first time a language is selected.
        if (response.ok && (APP_SHELL.includes(url.pathname) || url.pathname.startsWith("/locales/"))) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      }).catch(() => {
        // Final fallback: offline HTML for navigation requests
        if (request.mode === "navigate") {
          return new Response(OFFLINE_HTML, {
            status: 200,
            headers: { "Content-Type": "text/html" },
          });
        }
        return new Response("Offline", { status: 503 });
      });
    }),
  );
});
