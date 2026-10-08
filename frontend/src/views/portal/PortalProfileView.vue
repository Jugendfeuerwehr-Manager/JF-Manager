<script setup lang="ts">
import { reactive, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Select from 'primevue/select'
import MfaSettings from '@/components/MfaSettings.vue'
import SessionDevices from '@/components/security/SessionDevices.vue'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useTheme, type ThemeMode } from '@/composables/useTheme'
import { getApiErrorMessage } from '@/utils/apiError'

const auth = useAuthStore()
const { themeMode, setMode } = useTheme()

const pw = reactive({ old_password: '', new_password: '', new_password_confirm: '' })
const pwSaving = ref(false)
const pwMsg = ref<{ severity: 'success' | 'error', text: string } | null>(null)
const themes: { label: string, value: ThemeMode }[] = [
  { label: 'System', value: 'system' }, { label: 'Hell', value: 'light' }, { label: 'Dunkel', value: 'dark' },
]

async function changePassword() {
  pwMsg.value = null
  pwSaving.value = true
  try {
    await authApi.changePassword({ ...pw })
    pw.old_password = ''; pw.new_password = ''; pw.new_password_confirm = ''
    pwMsg.value = { severity: 'success', text: 'Das Passwort wurde geändert.' }
  } catch (err) {
    pwMsg.value = { severity: 'error', text: getApiErrorMessage(err, 'Das Passwort konnte nicht geändert werden.') }
  } finally {
    pwSaving.value = false
  }
}
</script>

<template>
  <div class="portal-profile">
    <h1>Profil</h1>

    <section class="card" aria-labelledby="acc">
      <h2 id="acc">Zugang</h2>
      <dl>
        <dt>Name</dt><dd>{{ auth.userFullName || '–' }}</dd>
        <dt>E-Mail</dt><dd>{{ auth.user?.email || auth.user?.username || '–' }}</dd>
      </dl>
    </section>

    <Message severity="info" :closable="false">
      Namen und Kontaktdaten pflegt die Jugendfeuerwehr. Änderungen beantragst du bald unter „Daten“; sie werden nach Prüfung übernommen.
    </Message>

    <section class="card" aria-labelledby="look">
      <h2 id="look">Darstellung</h2>
      <label for="p-theme">Farbschema</label>
      <Select input-id="p-theme" :model-value="themeMode" :options="themes" option-label="label" option-value="value" class="theme-select" @update:model-value="setMode" />
    </section>

    <section class="card" aria-labelledby="pwd">
      <h2 id="pwd">Passwort ändern</h2>
      <form class="form" @submit.prevent="changePassword">
        <label for="p-old">Aktuelles Passwort</label>
        <Password v-model="pw.old_password" input-id="p-old" :feedback="false" toggle-mask autocomplete="current-password" fluid />
        <label for="p-new">Neues Passwort</label>
        <Password v-model="pw.new_password" input-id="p-new" :feedback="false" toggle-mask autocomplete="new-password" fluid />
        <label for="p-new2">Neues Passwort wiederholen</label>
        <Password v-model="pw.new_password_confirm" input-id="p-new2" :feedback="false" toggle-mask autocomplete="new-password" fluid />
        <Message v-if="pwMsg" :severity="pwMsg.severity" :closable="false">{{ pwMsg.text }}</Message>
        <Button type="submit" label="Passwort ändern" icon="pi pi-lock" :loading="pwSaving" class="touch" />
      </form>
    </section>

    <section class="card"><MfaSettings /></section>
    <section class="card"><SessionDevices /></section>
  </div>
</template>

<style scoped>
.portal-profile { display: flex; flex-direction: column; gap: 1rem; min-width: 0; }
h1 { margin: 0; font-size: 1.5rem; }
h2 { margin: 0 0 0.75rem; font-size: 1.1rem; }
.card { padding: 1rem; border-radius: 0.75rem; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); min-width: 0; }
.form { display: flex; flex-direction: column; gap: 0.35rem; }
.form label, .card > label { font-size: 0.875rem; color: var(--p-text-muted-color); margin-top: 0.4rem; }
.form .touch { margin-top: 0.75rem; align-self: flex-start; }
.touch { min-height: 44px; }
.theme-select { width: 100%; max-width: 20rem; min-height: 44px; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 0.35rem 1rem; margin: 0; }
dt { color: var(--p-text-muted-color); }
dd { margin: 0; overflow-wrap: anywhere; }
</style>
