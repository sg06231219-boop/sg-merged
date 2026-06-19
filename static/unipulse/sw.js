/* UniPulse Service Worker - Cache static assets */
const CACHE = 'unipulse-v2';
const PRE_CACHE = [
  '/',
  '/index.html',
  '/css/style.css',
  '/js/main.js',
  '/js/data.js',
  '/js/state.js',
  '/js/router.js',
  '/js/render.js',
  '/js/compare.js'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(PRE_CACHE).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  /* Network-first for HTML, cache-first for assets */
  if (e.request.mode === 'navigate' || e.request.headers.get('accept')?.includes('text/html')) {
    e.respondWith(
      fetch(e.request).catch(() => caches.match('/index.html'))
    );
  } else {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request))
    );
  }
});
