<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { disableDevicePush, getWorker, installApp, installPrompt, pwaSupported, standalone } from '@/utils/pwa'

const auth = useAuthStore()
const supported = pwaSupported && 'PushManager' in window && 'Notification' in window
const enabled = ref(false)
const subscribed = ref(false)
const services = ref(true)
const orders = ref(true)
const loading = ref(true)
const busy = ref(false)
const feedback = ref('')
const failed = ref(false)
let publicKey = ''

async function run(action: () => Promise<void>) {
  busy.value = true
  feedback.value = ''
  failed.value = false
  try { await action() } catch (error) {
    failed.value = true
    feedback.value = error instanceof Error ? error.message : 'Die Aktion konnte nicht abgeschlossen werden.'
  } finally { busy.value = false }
}
async function save() {
  await run(async () => {
    if (!supported) return
    // Request permission directly from a user gesture (required by mobile browsers).
    if (await Notification.requestPermission() !== 'granted') {
      throw new Error('Mitteilungen sind nicht erlaubt. Du kannst dies in den Browser-Einstellungen ändern.')
    }
    const worker = await getWorker()
    let subscription = await worker.pushManager.getSubscription()
    if (subscription && localStorage.getItem('pushOwner') !== String(auth.user?.id)) {
      await subscription.unsubscribe()
      subscription = null
    }
    const decoded = atob(publicKey.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - publicKey.length % 4) % 4))
    const key = Uint8Array.from(decoded, (character) => character.charCodeAt(0))
    subscription ??= await worker.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key })
    await api.post('/push/subscription/', { ...subscription.toJSON(), services: services.value, orders: orders.value })
    localStorage.setItem('pushOwner', String(auth.user?.id))
    subscribed.value = true
    feedback.value = 'Push-Mitteilungen sind auf diesem Gerät aktiviert.'
  })
}
async function disable() {
  await run(async () => {
    const subscription = await (await getWorker()).pushManager.getSubscription()
    if (subscription) await api.delete('/push/subscription/', { data: { endpoint: subscription.endpoint } })
    await disableDevicePush()
    subscribed.value = false
    feedback.value = 'Push-Mitteilungen sind auf diesem Gerät ausgeschaltet.'
  })
}
async function test() {
  await run(async () => {
    const subscription = await (await getWorker()).pushManager.getSubscription()
    await api.post('/push/test/', { endpoint: subscription?.endpoint })
    feedback.value = 'Test-Mitteilung vorgemerkt. Der Versand kann einen Moment dauern.'
  })
}
onMounted(async () => {
  try {
    if (!supported) return
    const { data } = await api.get('/push/config/')
    enabled.value = data.enabled
    publicKey = data.public_key
    const subscription = await (await getWorker()).pushManager.getSubscription()
    if (subscription) {
      const { data: status } = await api.get('/push/subscription/', { params: { endpoint: subscription.endpoint } })
      subscribed.value = status.subscribed
      services.value = status.services
      orders.value = status.orders
    }
  } catch {
    failed.value = true
    feedback.value = 'Die Geräteeinstellungen konnten nicht geladen werden. Bitte Seite erneut öffnen.'
  } finally { loading.value = false }
})
</script>

<template>
  <section class="device-settings" aria-labelledby="device-heading">
    <h3 id="device-heading"><i class="pi pi-mobile" aria-hidden="true" /> App & Mitteilungen</h3>
    <p>Installiere den JF-Manager für direkten Zugriff vom Startbildschirm.</p>
    <Message v-if="standalone" severity="success" :closable="false">Du verwendest bereits die installierte Web-App.</Message>
    <Button v-else-if="installPrompt" label="App installieren" icon="pi pi-download" @click="run(installApp)" />
    <p v-else class="hint">Android/Desktop: Browser-Menü → „App installieren“. iPhone/iPad: Safari → Teilen → „Zum Home-Bildschirm“.</p>
    <p>Mitteilungen informieren dich über neue oder geänderte Dienste sowie neue Bestellungen und Statuswechsel. Auf dem Sperrbildschirm erscheinen keine Mitgliedernamen.</p>
    <Message v-if="!supported" severity="info" :closable="false">Dieser Browser unterstützt hier kein Push. Auf iPhone/iPad öffne die installierte Web-App; die Seite muss über HTTPS erreichbar sein.</Message>
    <Message v-else-if="!loading && !enabled" severity="info" :closable="false">Push wurde auf diesem Server noch nicht eingerichtet. Bitte die Administration ansprechen.</Message>
    <div v-else-if="!loading" class="push-controls">
      <label><Checkbox v-model="services" binary :disabled="busy" /> Dienste</label>
      <label><Checkbox v-model="orders" binary :disabled="busy" /> Bestellungen</label>
      <div class="actions">
        <Button :label="subscribed ? 'Auswahl speichern' : 'Mitteilungen aktivieren'" icon="pi pi-bell" :loading="busy" @click="save" />
        <Button v-if="subscribed" label="Test senden" severity="secondary" :disabled="busy" @click="test" />
        <Button v-if="subscribed" label="Ausschalten" severity="secondary" outlined :disabled="busy" @click="disable" />
      </div>
      <p class="hint">Die Auswahl gilt nur für dieses Gerät. Nach dem Abmelden musst du Push erneut aktivieren. Für Daten und Änderungen ist eine Internetverbindung erforderlich.</p>
    </div>
    <Message v-if="feedback" :severity="failed ? 'error' : 'success'" :closable="false" role="status">{{ feedback }}</Message>
  </section>
</template>

<style scoped>
.device-settings { display: grid; gap: 1rem; }
h3 { display: flex; align-items: center; gap: .5rem; }
p { line-height: 1.6; }
.hint { color: var(--p-text-muted-color); font-size: .9rem; }
.push-controls { display: grid; gap: 1rem; }
label, .actions { display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; }
</style>
