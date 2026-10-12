// Musk Wire service worker: lets the app open offline and always tries the network first for headlines.
const CACHE = "musk-wire-v3";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  // Headlines and the page itself: network first, fall back to the last saved copy.
  if (url.pathname.endsWith("/data/news.json") || e.request.mode === "navigate") {
    const key = url.pathname.endsWith("/data/news.json") ? new Request(url.origin + url.pathname) : e.request;
    e.respondWith(
      fetch(e.request).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(key, copy)); }
        return res;
      }).catch(() => caches.match(key).then(r => r || caches.match("index.html")))
    );
    return;
  }

  // Icons and other static files: cache first.
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
