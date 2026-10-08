/* Only public offline assets are cached. API responses and personal data never are. */
const CACHE = 'jf-public-v1'
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(['/offline.html', '/icons/icon-192.png'])))
  self.skipWaiting()
})
self.addEventListener('activate', (event) => {
  event.waitUntil(Promise.all([
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith('jf-public-') && key !== CACHE).map((key) => caches.delete(key)))),
    self.clients.claim(),
  ]))
})
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (url.origin !== self.location.origin || event.request.method !== 'GET') return
  if (event.request.mode === 'navigate' && !/^\/(api|admin|accounts|uploads|static)(\/|$)/.test(url.pathname)) {
    event.respondWith(fetch(event.request).catch(() => caches.match('/offline.html')))
  }
})
self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data?.json() || {} } catch { /* use generic fallback */ }
  event.waitUntil(self.registration.showNotification(data.title || 'JF-Manager', {
    body: data.body || 'Es gibt Neuigkeiten im JF-Manager.',
    icon: '/icons/icon-192.png', badge: '/icons/icon-192.png',
    tag: data.tag || 'jf-update', data: { url: data.url || '/' },
  }))
})
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL(event.notification.data?.url || '/', self.location.origin)
  if (target.origin !== self.location.origin) return
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (clients) => {
    for (const client of clients) {
      if ('navigate' in client) {
        await client.navigate(target.href)
        return client.focus()
      }
    }
    return self.clients.openWindow(target.href)
  }))
})
