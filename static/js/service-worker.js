const CACHE_NAME = "faceedu-v1";
const urlsToCache = [
  "/",
  "/static/css/",
  "/static/js/",
  "/static/icons/logo.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
