<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { disableDevicePush, getWorker, pwaSupported } from '@/utils/pwa'

const auth = useAuthStore()
const supported = pwaSupported && 'PushManager' in window && 'Notification' in window
const enabled = ref(false)
const subscribed = ref(false)
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
async function enable() {
  await run(async () => {
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
    await api.post('/push/subscription/', { ...subscription.toJSON(), participation: true })
    localStorage.setItem('pushOwner', String(auth.user?.id))
    subscribed.value = true
    feedback.value = 'Push ist auf diesem Gerät aktiviert.'
  })
}
async function disable() {
  await run(async () => {
    const subscription = await (await getWorker()).pushManager.getSubscription()
    if (subscription) await api.delete('/push/subscription/', { data: { endpoint: subscription.endpoint } })
    await disableDevicePush()
    subscribed.value = false
    feedback.value = 'Push ist auf diesem Gerät ausgeschaltet.'
  })
}
onMounted(async () => {
  try {
    if (!supported) return
    const { data } = await api.get('/push/config/')
    enabled.value = data.enabled
    publicKey = data.public_key
    if (!enabled.value) return
    const subscription = await (await getWorker()).pushManager.getSubscription()
    if (subscription) {
      const { data: status } = await api.get('/push/subscription/', { params: { endpoint: subscription.endpoint } })
      subscribed.value = status.subscribed
    }
  } catch {
    enabled.value = false
  } finally { loading.value = false }
})
</script>

<template>
  <section v-if="supported && !loading && enabled" class="push-card" aria-labelledby="push-heading">
    <h2 id="push-heading"><i class="pi pi-mobile" aria-hidden="true" /> Push auf diesem Gerät</h2>
    <p>Hinweise zur Teilnahme erscheinen als Push-Mitteilung. Auf dem Sperrbildschirm stehen keine Namen. Die Einstellung gilt nur für dieses Gerät.</p>
    <Button v-if="!subscribed" label="Push aktivieren" icon="pi pi-bell" :loading="busy" class="touch" @click="enable" />
    <Button v-else label="Push ausschalten" icon="pi pi-bell-slash" severity="secondary" outlined :loading="busy" class="touch" @click="disable" />
    <Message v-if="feedback" :severity="failed ? 'error' : 'success'" :closable="false" role="status">{{ feedback }}</Message>
  </section>
</template>

<style scoped>
.push-card { display: flex; flex-direction: column; gap: .75rem; align-items: flex-start; padding: 14px; border-radius: 14px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
h2 { margin: 0; font-size: 1.1rem; display: flex; align-items: center; gap: .5rem; }
p { margin: 0; line-height: 1.5; color: var(--p-text-muted-color); font-size: .9rem; }
.touch { min-height: 44px; }
</style>
