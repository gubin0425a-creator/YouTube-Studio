"use strict";

const CACHE = "youtube-studio-shell-v2";
const SCOPE_URL = new URL(self.registration.scope);
const scopePath = SCOPE_URL.pathname.endsWith("/") ? SCOPE_URL.pathname : `${SCOPE_URL.pathname}/`;
const scoped = path => new URL(path, self.registration.scope).toString();
const SHELL = [
  scoped("./"),
  scoped("manifest.webmanifest"),
  scoped("assets/icon-192.png"),
  scoped("assets/icon-512.png"),
  scoped("assets/favicon.png")
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never cache login, chat, images, configuration, render, or health data.
  const relativePath = url.pathname.startsWith(scopePath)
    ? url.pathname.slice(scopePath.length - 1)
    : url.pathname;
  if (relativePath.startsWith("/v1/") || relativePath === "/health") return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(scoped("./"), copy));
          return response;
        })
        .catch(() => caches.match(scoped("./")))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(request, copy));
      }
      return response;
    }))
  );
});
