import { ref } from 'vue'

interface InstallPrompt extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}
export const installPrompt = ref<InstallPrompt | null>(null)
export const standalone = ref(window.matchMedia?.('(display-mode: standalone)')?.matches ?? false)
export const pwaSupported = 'serviceWorker' in navigator && window.isSecureContext
let registration: Promise<ServiceWorkerRegistration> | undefined

export function registerPwa() {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    installPrompt.value = event as InstallPrompt
  })
  window.addEventListener('appinstalled', () => {
    installPrompt.value = null
    standalone.value = true
  })
  if (pwaSupported) {
    registration = navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' })
    registration.catch(() => { /* profile shows registration errors when requested */ })
  }
}

export async function getWorker() {
  if (!pwaSupported) throw new Error('Die Web-App benötigt HTTPS und einen unterstützten Browser.')
  await (registration ?? navigator.serviceWorker.register('/sw.js'))
  return Promise.race([
    navigator.serviceWorker.ready,
    new Promise<never>((_, reject) => setTimeout(() => reject(new Error('Die Web-App konnte nicht gestartet werden. Bitte Seite neu laden.')), 10000)),
  ])
}

export async function disableDevicePush() {
  localStorage.removeItem('pushOwner')
  if (!pwaSupported) return
  const worker = await navigator.serviceWorker.getRegistration('/')
  const subscription = await worker?.pushManager.getSubscription()
  await subscription?.unsubscribe()
}

export async function installApp() {
  if (!installPrompt.value) return
  const prompt = installPrompt.value
  await prompt.prompt()
  await prompt.userChoice
  installPrompt.value = null
}
