<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { authApi, type DeviceSession } from '@/api/auth'
import { getApiErrorMessage } from '@/utils/apiError'
import { hardNavigate } from '@/utils/navigation'
import { describeUserAgent } from '@/utils/userAgent'

const devices = ref<DeviceSession[]>([])
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const success = ref('')

const dateFormat = new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' })
const formatDate = (value: string) => dateFormat.format(new Date(value))

async function load() {
  loading.value = true
  error.value = ''
  try {
    devices.value = (await authApi.devices()).data
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Die angemeldeten Geräte konnten nicht geladen werden.')
  } finally {
    loading.value = false
  }
}

async function revoke(action: () => Promise<{ data: { revoked: number; current: boolean } }>) {
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    const { data } = await action()
    if (data.current) {
      hardNavigate('/login')
      return
    }
    success.value = data.revoked === 1 ? 'Ein Gerät wurde abgemeldet.' : `${data.revoked} Geräte wurden abgemeldet.`
    await load()
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Das Abmelden ist fehlgeschlagen.')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="session-devices" aria-labelledby="devices-heading">
    <h3 id="devices-heading"><i class="pi pi-desktop" aria-hidden="true" /> Angemeldete Geräte</h3>
    <p class="hint">
      Hier siehst du, wo du gerade angemeldet bist. Unbekannte Geräte meldest du ab und änderst danach dein Passwort.
    </p>
    <p v-if="loading" class="hint" role="status">Wird geladen…</p>
    <ul v-else class="device-list">
      <li v-for="device in devices" :key="device.id" class="device">
        <div class="device-info">
          <strong>{{ describeUserAgent(device.user_agent) }}</strong>
          <Tag v-if="device.current" value="Dieses Gerät" severity="info" />
          <span class="hint">Angemeldet {{ formatDate(device.created_at) }} · zuletzt aktiv {{ formatDate(device.last_seen_at) }}</span>
        </div>
        <Button
          :label="device.current ? 'Hier abmelden' : 'Abmelden'"
          icon="pi pi-sign-out"
          severity="secondary"
          outlined
          :disabled="busy"
          :aria-label="`${describeUserAgent(device.user_agent)} abmelden`"
          @click="revoke(() => authApi.revokeDevice(device.id))"
        />
      </li>
    </ul>
    <div v-if="devices.length > 1" class="actions">
      <Button label="Alle anderen Geräte abmelden" icon="pi pi-power-off" severity="danger" outlined :loading="busy" @click="revoke(authApi.revokeOtherDevices)" />
    </div>
    <Message v-if="error" severity="error" role="alert">{{ error }}</Message>
    <Message v-if="success" severity="success" role="status">{{ success }}</Message>
  </section>
</template>

<style scoped>
.session-devices { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 2rem; }
.session-devices h3 { display: flex; align-items: center; gap: .5rem; margin: 0; }
.hint { color: var(--text-color-secondary); font-size: .9rem; margin: 0; }
.device-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .75rem; }
.device { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .75rem; padding: .75rem 1rem; border: 1px solid var(--surface-border, #d9dee5); border-radius: 8px; }
.device-info { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; }
.device-info .hint { flex-basis: 100%; }
.actions :deep(.p-button), .device :deep(.p-button) { min-height: 44px; }
</style>
