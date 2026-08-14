// ============================================================
// StudyVerse Service Worker — PWA Support
// Caches core assets; serves stale-while-revalidate for pages
// ============================================================

const CACHE_NAME = 'studyverse-v1';

// Assets to cache immediately on install
const PRECACHE_URLS = [
  '/',
  '/dashboard',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
  '/static/img/favicon.png',
  '/offline'
];

// ── Install: pre-cache shell assets ──────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Cache what we can; ignore failures for dynamic routes
      return cache.addAll(PRECACHE_URLS).catch(() => {});
    })
  );
  self.skipWaiting();
});

// ── Activate: clean up old caches ────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch: Network-first for pages, Cache-first for assets ───
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, cross-origin, socket.io requests
  if (
    request.method !== 'GET' ||
    !url.origin.includes(self.location.origin) ||
    url.pathname.startsWith('/socket.io')
  ) {
    return;
  }

  // Static assets → Cache-first
  if (
    url.pathname.startsWith('/static/') ||
    url.pathname.match(/\.(png|jpg|jpeg|gif|ico|svg|woff2?|ttf|css|js)$/)
  ) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // HTML/API pages → Network-first with offline fallback
  event.respondWith(
    fetch(request)
      .then(response => {
        // Cache successful page responses
        if (response.ok && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        }
        return response;
      })
      .catch(() =>
        // Network failed → try cache, else offline page
        caches.match(request).then(cached => {
          if (cached) return cached;
          return caches.match('/offline') || new Response(
            '<h1 style="font-family:sans-serif;text-align:center;margin-top:20vh;color:#0ea5e9">📚 StudyVerse<br><small style="color:#666;font-size:0.5em">You\'re offline. Reconnect to continue studying!</small></h1>',
            { headers: { 'Content-Type': 'text/html' } }
          );
        })
      )
  );
});
