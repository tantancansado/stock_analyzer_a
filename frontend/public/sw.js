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

// ── Web Push ──────────────────────────────────────────────────────────────────
self.addEventListener('push', e => {
  let data = {}
  try { data = e.data?.json() ?? {} } catch { data = { title: 'Stock Analyzer', body: e.data?.text() ?? '' } }

  const title   = data.title ?? 'Stock Analyzer'
  const options = {
    body:    data.body ?? '',
    tag:     data.tag  ?? 'sa-alert',
    icon:    '/stock_analyzer_a/app/icon-192.png',
    badge:   '/stock_analyzer_a/app/icon-192.png',
    data:    { url: data.url ?? '/stock_analyzer_a/app/' },
    requireInteraction: false,
    silent:  false,
  }
  e.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', e => {
  e.notification.close()
  const url = e.notification.data?.url ?? '/stock_analyzer_a/app/'
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      const match = list.find(c => c.url.includes('/stock_analyzer_a/app'))
      if (match) { match.focus(); return match.navigate(url) }
      return clients.openWindow(url)
    })
  )
})
