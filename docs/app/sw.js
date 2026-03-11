// Minimal service worker — cache-first for static assets, network-first for API
const CACHE = 'sa-v1'
const STATIC = ['/app/', '/app/index.html']

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC).catch(() => {})))
  self.skipWaiting()
})

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url)
  // Network-first for API calls
  if (url.pathname.startsWith('/api/')) return
  // Cache-first for everything else
  e.respondWith(
    caches.match(e.request).then(cached => cached ?? fetch(e.request))
  )
})
