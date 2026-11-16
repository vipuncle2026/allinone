const CACHE_NAME = 'allinone-v2';

// 需要预缓存的静态资源（构建后会自动更新）
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
];

// install: 预缓存核心资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

// activate: 清理旧版本缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// fetch: 网络优先策略（适合局域网内使用）
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API 和个人上传文件包含敏感数据，始终直连网络且不进入 Cache Storage。
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/uploads/')) {
    return;
  }

  // 静态资源：缓存优先（加速加载）
  if (request.destination === 'image' || request.destination === 'font') {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // 其他请求（HTML/JS/CSS）：网络优先
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (request.method === 'GET' && response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, clone);
          });
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        // HTML 请求回退到 index.html（SPA 路由）
        if (request.mode === 'navigate') {
          const fallback = await caches.match('/index.html');
          if (fallback) return fallback;
        }
        return new Response('离线', { status: 503 });
      })
  );
});
