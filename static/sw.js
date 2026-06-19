// Service Worker for Auto Site Builder PWA
const CACHE_NAME = 'autosite-v1';
const STATIC_ASSETS = [
  '/',
  '/static/index.html',
  '/static/manifest.json',
  '/static/favicon.ico',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// 安装事件 - 缓存静态资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// 请求拦截 - 网络优先，缓存后备（API 调用需要实时数据）
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API 请求走网络
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .catch(() => new Response(JSON.stringify({ error: '离线状态，请检查网络' }), {
          headers: { 'Content-Type': 'application/json' }
        }))
    );
    return;
  }

  // 静态资源 - 缓存优先
  event.respondWith(
    caches.match(request)
      .then((cached) => cached || fetch(request).then((response) => {
        // 缓存新资源
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
        }
        return response;
      }))
  );
});
