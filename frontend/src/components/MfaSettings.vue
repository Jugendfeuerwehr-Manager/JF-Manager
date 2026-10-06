<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { authApi, type MFASetup, type MFAStatus, type Passkey } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { getApiErrorMessage } from '@/utils/apiError'
import { createPasskey, passkeyErrorMessage, passkeysSupported } from '@/utils/webauthn'

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

const qrCode = ref('')
const passkeyName = ref('')
const canUsePasskeys = passkeysSupported()
const passkeys = computed<Passkey[]>(() => status.value?.passkeys ?? [])
/** Mandatory MFA keeps at least one factor; the server enforces the same rule. */
const factorCount = computed(() => (status.value?.totp_enabled ? 1 : 0) + passkeys.value.length)
const canRemoveFactor = computed(() => !status.value?.required || factorCount.value > 1)

const dateFormat = new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium' })
function formatDate(value: string | null) {
  return value ? dateFormat.format(new Date(value)) : 'noch nie'
}

const groupedSecret = computed(() => setup.value?.secret.match(/.{1,4}/g)?.join(' ') ?? '')

// Rendered locally: the TOTP secret must never be sent to a third-party QR service.
watch(setup, async (value) => {
  qrCode.value = ''
  if (!value) return
  try {
    const svg = await QRCode.toString(value.otpauth_uri, { type: 'svg', errorCorrectionLevel: 'M', margin: 4 })
    if (setup.value === value) qrCode.value = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  } catch {
    // The manual key and app link below remain usable.
  }
})

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
      : passkeyErrorMessage(err) ?? getApiErrorMessage(err, 'Die Aktion konnte nicht abgeschlossen werden.')
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
    success.value = 'Die Authenticator-App ist eingerichtet.'
    // Lifts a mandatory-setup restriction for this session.
    await auth.refreshSession()
  })
}

function addPasskey() {
  return run(async () => {
    const options = (await authApi.passkeyRegisterOptions()).data
    const credential = await createPasskey(options)
    const response = await authApi.passkeyRegister(credential, passkeyName.value.trim())
    status.value = response.data
    recoveryCodes.value = response.data.recovery_codes
    passkeyName.value = ''
    success.value = 'Der Passkey wurde hinzugefügt.'
    await auth.refreshSession()
  })
}

function removePasskey(passkey: Passkey) {
  return run(async () => {
    status.value = (await authApi.passkeyRemove(passkey.id)).data
    success.value = `Passkey „${passkey.name}“ wurde entfernt.`
  })
}

function removeTotp() {
  return run(async () => {
    status.value = (await authApi.mfaTotpRemove()).data
    success.value = 'Die Authenticator-App wurde entfernt.'
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
    success.value = 'Zwei-Faktor-Anmeldung wurde deaktiviert; Authenticator-App und Passkeys sind entfernt.'
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
  // With passkey support the person chooses between passkey and app; otherwise start the app setup.
  if (props.setupRequested && status.value && !status.value.enabled && !setup.value && !canUsePasskeys) await startSetup()
})
</script>

<template>
  <section class="mfa-settings" aria-labelledby="mfa-heading">
    <h3 id="mfa-heading"><i class="pi pi-shield" aria-hidden="true" /> Zwei-Faktor-Anmeldung</h3>
    <Message v-if="auth.mfaSetupRequired" severity="warn" :closable="false">
      Für die Rollen dieses Kontos ist eine Zwei-Faktor-Anmeldung verpflichtend. Bitte richte sie ein, um fortzufahren.
    </Message>
    <p class="hint">
      Zusätzlich zum Passwort bestätigst du die Anmeldung mit einem Passkey (Fingerabdruck, Gesichtserkennung,
      Geräte-PIN oder Sicherheitsschlüssel) oder mit einem Code aus einer Authenticator-App
      (z. B. Aegis, Google Authenticator, Microsoft Authenticator oder ein Passwortmanager). Beides kann parallel genutzt werden.
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
            Öffne deine Authenticator-App, füge ein Konto hinzu und scanne diesen QR-Code.
            <img
              v-if="qrCode"
              :src="qrCode"
              class="qr-code"
              width="200"
              height="200"
              alt="QR-Code zum Einrichten der Authenticator-App"
            />
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
          falls weder Passkey noch Authenticator-App verfügbar sind.
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

      <div v-if="!setup && !recoveryCodes.length" class="factor" aria-labelledby="mfa-passkeys-heading">
        <h4 id="mfa-passkeys-heading"><i class="pi pi-key" aria-hidden="true" /> Passkeys</h4>
        <ul v-if="passkeys.length" class="passkey-list">
          <li v-for="passkey in passkeys" :key="passkey.id">
            <span class="passkey-name">{{ passkey.name }}</span>
            <span class="hint">hinzugefügt {{ formatDate(passkey.created_at) }}, zuletzt genutzt {{ formatDate(passkey.last_used_at) }}</span>
            <Button
              :aria-label="`Passkey ${passkey.name} entfernen`"
              label="Entfernen"
              icon="pi pi-trash"
              severity="danger"
              text
              :disabled="busy || !canRemoveFactor"
              @click="removePasskey(passkey)"
            />
          </li>
        </ul>
        <p v-else class="hint">Noch kein Passkey hinzugefügt.</p>
        <form v-if="canUsePasskeys" class="inline-form" @submit.prevent="addPasskey">
          <label for="passkey-name" class="sr-only">Name des Passkeys</label>
          <InputText id="passkey-name" v-model="passkeyName" maxlength="64" placeholder="Name, z. B. Smartphone" />
          <Button type="submit" label="Passkey hinzufügen" icon="pi pi-plus" :loading="busy" />
        </form>
        <p v-else class="hint">Dieser Browser unterstützt keine Passkeys. Nutze die Authenticator-App oder einen aktuellen Browser.</p>
      </div>

      <div v-if="!setup && !recoveryCodes.length" class="factor" aria-labelledby="mfa-totp-heading">
        <h4 id="mfa-totp-heading"><i class="pi pi-mobile" aria-hidden="true" /> Authenticator-App</h4>
        <div class="actions">
          <Tag v-if="status.totp_enabled" value="Eingerichtet" severity="success" icon="pi pi-check" />
          <Button v-if="!status.totp_enabled" label="Authenticator-App einrichten" icon="pi pi-shield" severity="secondary" :loading="busy" @click="startSetup" />
          <Button v-else label="Entfernen" icon="pi pi-trash" severity="danger" text :disabled="busy || !canRemoveFactor" @click="removeTotp" />
        </div>
      </div>

      <p v-if="status.required && status.enabled && !canRemoveFactor" class="hint">
        Der letzte zweite Faktor eines Kontos mit verpflichtender Zwei-Faktor-Anmeldung kann nicht entfernt werden. Richte zuerst einen weiteren ein.
      </p>

      <div v-if="!setup && !recoveryCodes.length && status.enabled" class="actions">
        <Button label="Neue Wiederherstellungscodes" icon="pi pi-refresh" severity="secondary" :loading="busy" @click="regenerateCodes" />
        <Button v-if="!status.required" label="Zwei-Faktor-Anmeldung deaktivieren" icon="pi pi-times" severity="danger" outlined :disabled="busy" @click="disableMfa" />
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
.factor { display: flex; flex-direction: column; gap: .5rem; }
.factor h4 { display: flex; align-items: center; gap: .5rem; margin: 0; font-size: 1rem; }
.passkey-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .25rem; }
.passkey-list li { display: flex; flex-wrap: wrap; align-items: center; gap: .25rem .75rem; }
.passkey-name { font-weight: 600; }
.setup-box, .codes-box { display: flex; flex-direction: column; gap: 1rem; padding: 1rem; border: 1px solid var(--surface-border, #d9dee5); border-radius: 8px; }
.setup-box ol { margin: 0; padding-left: 1.25rem; display: flex; flex-direction: column; gap: .5rem; }
.qr-code { display: block; width: 200px; height: 200px; margin: .75rem 0 .25rem; background: #fff; border-radius: 8px; }
.app-link { display: inline-block; margin-left: .25rem; color: var(--primary-color); }
.secret { display: block; margin-top: .4rem; font-size: 1.05rem; letter-spacing: .08em; word-break: break-all; }
.codes { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr)); gap: .5rem; }
.codes code { font-size: 1rem; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
