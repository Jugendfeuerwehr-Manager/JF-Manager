<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { authApi, type MFASetup, type MFAStatus } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { getApiErrorMessage } from '@/utils/apiError'

const props = defineProps<{ setupRequested?: boolean }>()

const auth = useAuthStore()
const status = ref<MFAStatus | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const success = ref('')
const setup = ref<MFASetup | null>(null)
const confirmCode = ref('')
const recoveryCodes = ref<string[]>([])

const groupedSecret = computed(() => setup.value?.secret.match(/.{1,4}/g)?.join(' ') ?? '')

function errorCode(err: unknown): string | undefined {
  return (err as { response?: { data?: { code?: string } } }).response?.data?.code
}

async function loadStatus() {
  loading.value = true
  try {
    status.value = (await authApi.mfaStatus()).data
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Der MFA-Status konnte nicht geladen werden.')
  } finally {
    loading.value = false
  }
}

async function run(action: () => Promise<void>) {
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    await action()
  } catch (err) {
    // The global step-up dialog already asked; a remaining 403 means it was cancelled.
    error.value = errorCode(err) === 'reauthentication_required'
      ? 'Die Bestätigung wurde abgebrochen. Die Änderung wurde nicht gespeichert.'
      : getApiErrorMessage(err, 'Die Aktion konnte nicht abgeschlossen werden.')
  } finally {
    busy.value = false
  }
}

function startSetup() {
  return run(async () => {
    setup.value = (await authApi.mfaSetup()).data
    confirmCode.value = ''
  })
}

function confirmSetup() {
  return run(async () => {
    const response = await authApi.mfaConfirm(confirmCode.value.trim())
    recoveryCodes.value = response.data.recovery_codes
    setup.value = null
    status.value = response.data
    success.value = 'Zwei-Faktor-Anmeldung ist aktiv.'
    // Lifts a mandatory-setup restriction for this session.
    await auth.refreshSession()
  })
}

function regenerateCodes() {
  return run(async () => {
    recoveryCodes.value = (await authApi.mfaRecoveryCodes()).data.recovery_codes
    await loadStatus()
  })
}

function disableMfa() {
  return run(async () => {
    status.value = (await authApi.mfaDisable()).data
    recoveryCodes.value = []
    success.value = 'Zwei-Faktor-Anmeldung wurde deaktiviert.'
  })
}

async function copyCodes() {
  await navigator.clipboard.writeText(recoveryCodes.value.join('\n'))
  success.value = 'Wiederherstellungscodes kopiert.'
}

function downloadCodes() {
  const blob = new Blob([`JF-Manager Wiederherstellungscodes\n\n${recoveryCodes.value.join('\n')}\n`], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'jf-manager-wiederherstellungscodes.txt'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

onMounted(async () => {
  await loadStatus()
  if (props.setupRequested && status.value && !status.value.enabled && !setup.value) await startSetup()
})
</script>

<template>
  <section class="mfa-settings" aria-labelledby="mfa-heading">
    <h3 id="mfa-heading"><i class="pi pi-shield" aria-hidden="true" /> Zwei-Faktor-Anmeldung</h3>
    <Message v-if="auth.mfaSetupRequired" severity="warn" :closable="false">
      Für die Rollen dieses Kontos ist eine Zwei-Faktor-Anmeldung verpflichtend. Bitte richte sie ein, um fortzufahren.
    </Message>
    <p class="hint">
      Zusätzlich zum Passwort fragt JF-Manager einen sechsstelligen Code aus einer Authenticator-App ab
      (z. B. Aegis, Google Authenticator, Microsoft Authenticator oder ein Passwortmanager).
    </p>

    <p v-if="loading" class="hint" role="status">Wird geladen…</p>
    <template v-else-if="status">
      <div class="status-row">
        <Tag v-if="status.enabled" value="Aktiv" severity="success" icon="pi pi-check" />
        <Tag v-else value="Nicht eingerichtet" severity="secondary" icon="pi pi-minus-circle" />
        <Tag v-if="status.required" value="Verpflichtend" severity="warn" icon="pi pi-lock" />
        <span v-if="status.enabled" class="hint">{{ status.recovery_codes_remaining }} Wiederherstellungscodes übrig</span>
      </div>

      <div v-if="setup" class="setup-box">
        <ol>
          <li>
            Öffne deine Authenticator-App und füge ein Konto hinzu.
            <a :href="setup.otpauth_uri" class="app-link">Auf diesem Gerät direkt in der App öffnen</a>
          </li>
          <li>
            Oder gib diesen Schlüssel manuell ein (zeitbasiert, 6 Ziffern):
            <code class="secret" aria-label="Geheimer Schlüssel">{{ groupedSecret }}</code>
          </li>
          <li>Gib zur Bestätigung den angezeigten Code ein.</li>
        </ol>
        <form class="inline-form" @submit.prevent="confirmSetup">
          <label for="mfa-confirm-code" class="sr-only">Bestätigungscode</label>
          <InputText id="mfa-confirm-code" v-model="confirmCode" inputmode="numeric" autocomplete="one-time-code" placeholder="123456" required />
          <Button type="submit" label="Aktivieren" icon="pi pi-check" :loading="busy" />
          <Button type="button" label="Abbrechen" severity="secondary" text :disabled="busy" @click="setup = null" />
        </form>
      </div>

      <div v-if="recoveryCodes.length" class="codes-box" role="region" aria-label="Wiederherstellungscodes">
        <Message severity="warn" :closable="false">
          Speichere diese Codes jetzt sicher. Sie werden nur einmal angezeigt; jeder Code funktioniert genau einmal,
          falls dein Authenticator nicht verfügbar ist.
        </Message>
        <ul class="codes">
          <li v-for="code in recoveryCodes" :key="code"><code>{{ code }}</code></li>
        </ul>
        <div class="actions">
          <Button label="Kopieren" icon="pi pi-copy" severity="secondary" @click="copyCodes" />
          <Button label="Als Datei speichern" icon="pi pi-download" severity="secondary" @click="downloadCodes" />
          <Button label="Ich habe die Codes gespeichert" icon="pi pi-check" text @click="recoveryCodes = []" />
        </div>
      </div>

      <div v-if="!setup && !recoveryCodes.length" class="actions">
        <Button v-if="!status.enabled" label="Einrichten" icon="pi pi-shield" :loading="busy" @click="startSetup" />
        <template v-else>
          <Button label="Neue Wiederherstellungscodes" icon="pi pi-refresh" severity="secondary" :loading="busy" @click="regenerateCodes" />
          <Button v-if="!status.required" label="Deaktivieren" icon="pi pi-times" severity="danger" outlined :disabled="busy" @click="disableMfa" />
        </template>
      </div>
    </template>

    <Message v-if="error" severity="error" role="alert">{{ error }}</Message>
    <Message v-if="success" severity="success" role="status">{{ success }}</Message>

  </section>
</template>

<style scoped>
.mfa-settings { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 2rem; }
.mfa-settings h3 { display: flex; align-items: center; gap: .5rem; margin: 0; }
.hint { color: var(--text-color-secondary); font-size: .95rem; margin: 0; }
.status-row, .actions, .inline-form { display: flex; flex-wrap: wrap; align-items: center; gap: .75rem; }
.actions :deep(.p-button), .inline-form :deep(.p-button), .inline-form :deep(input) { min-height: 44px; }
.setup-box, .codes-box { display: flex; flex-direction: column; gap: 1rem; padding: 1rem; border: 1px solid var(--surface-border, #d9dee5); border-radius: 8px; }
.setup-box ol { margin: 0; padding-left: 1.25rem; display: flex; flex-direction: column; gap: .5rem; }
.app-link { display: inline-block; margin-left: .25rem; color: var(--primary-color); }
.secret { display: block; margin-top: .4rem; font-size: 1.05rem; letter-spacing: .08em; word-break: break-all; }
.codes { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr)); gap: .5rem; }
.codes code { font-size: 1rem; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
