<template>
  <main class="login-page">
    <section class="login-intro" aria-label="JF-Manager">
      <div class="brand">
        <img v-if="branding?.logo_url" :src="branding.logo_url" alt="Logo der Jugendfeuerwehr" />
        <i v-else class="pi pi-shield" aria-hidden="true"></i>
        <span>{{ branding?.title || 'JF-Manager' }}</span>
      </div>
      <div class="intro-copy">
        <p class="eyebrow">Für eure Jugendfeuerwehr</p>
        <h1>Mehr Zeit für<br />euer Team.</h1>
        <p>Mitglieder, Dienste und Ausbildung. Alles an einem Ort, damit ihr euch auf das Wesentliche konzentrieren könnt.</p>
        <div class="intro-modules"><span><i class="pi pi-users" aria-hidden="true"></i> Mitglieder</span><span><i class="pi pi-book" aria-hidden="true"></i> Dienstbuch</span><span><i class="pi pi-calendar" aria-hidden="true"></i> Ausbildung</span></div>
      </div>
      <p class="intro-footer">Gemeinsam organisiert. Gemeinsam stark.</p>
    </section>

    <section class="login-panel" aria-labelledby="login-heading">
      <div class="login-form-wrap">
        <p class="eyebrow">{{ branding?.slug || 'Willkommen zurück' }}</p>
        <h2 id="login-heading">{{ mfaStep ? 'Bestätigung' : 'Anmelden' }}</h2>
        <p class="login-description">{{ mfaStep ? mfaDescription : 'Melde dich mit deinem Zugang an.' }}</p>
        <form v-if="mfaStep" class="login-form" :aria-busy="loading" @submit.prevent="handleMfa">
          <Message v-if="error" id="login-error" severity="error" role="alert">{{ error }}</Message>
          <Button
            v-if="offerPasskey"
            type="button"
            label="Mit Passkey bestätigen"
            icon="pi pi-key"
            :severity="showCodeField ? 'secondary' : undefined"
            :loading="loading && passkeyBusy"
            :disabled="loading && !passkeyBusy"
            @click="handlePasskey"
          />
          <div v-if="offerPasskey && showCodeField" class="divider"><span>oder mit Code</span></div>
          <div v-if="showCodeField" class="field">
            <label for="mfa-code">{{ useRecoveryCode ? 'Wiederherstellungscode' : 'Bestätigungscode' }}</label>
            <InputText
              id="mfa-code"
              v-model="mfaCode"
              name="one-time-code"
              :autocomplete="useRecoveryCode ? 'off' : 'one-time-code'"
              :inputmode="useRecoveryCode ? 'text' : 'numeric'"
              autocapitalize="none"
              :spellcheck="false"
              required
              :autofocus="!offerPasskey"
              :invalid="!!error"
              :aria-describedby="error ? 'login-error' : undefined"
            />
          </div>
          <Button v-if="showCodeField" type="submit" label="Bestätigen" icon="pi pi-check" :loading="loading && !passkeyBusy" :disabled="passkeyBusy" />
          <button type="button" class="text-link" @click="toggleRecoveryCode">{{ useRecoveryCode ? (hasTotp ? 'Authenticator-Code verwenden' : 'Passkey verwenden') : 'Wiederherstellungscode verwenden' }}</button>
          <button type="button" class="text-link" @click="restartLogin">Abbrechen und neu anmelden</button>
        </form>
        <form v-else class="login-form" :aria-busy="loading || oidcLoading" @submit.prevent="handleLogin">
          <Message v-if="info" severity="info" role="status">{{ info }}</Message>
          <Message v-if="error" id="login-error" severity="error" role="alert">{{ error }}</Message>
          <template v-if="canUsePasskeys">
            <Button type="button" label="Mit Passkey anmelden" icon="pi pi-key" :loading="passkeyBusy" :disabled="(loading && !passkeyBusy) || oidcLoading" @click="handlePasskeySignIn" />
            <div v-if="!oidcConfig?.enabled" class="divider"><span>oder mit Benutzername</span></div>
          </template>
          <template v-if="oidcConfig?.enabled">
            <Button type="button" :label="`Mit ${oidcConfig.provider_name} anmelden`" icon="pi pi-sign-in" :loading="oidcLoading" :disabled="loading" @click="handleOIDCLogin" />
            <button v-if="oidcConfig.hide_local_login && !showLocalLogin" type="button" class="text-link" @click="showLocalLogin = true">Lokalen Account verwenden</button>
            <div v-if="!oidcConfig.hide_local_login || showLocalLogin" class="divider"><span>oder mit Benutzername</span></div>
          </template>
          <template v-if="!oidcConfig?.enabled || !oidcConfig.hide_local_login || showLocalLogin">
            <div class="field">
              <label for="username">Benutzername</label>
              <InputText id="username" v-model="username" name="username" autocomplete="username" autocapitalize="none" :spellcheck="false" required autofocus :invalid="!!error" :aria-describedby="error ? 'login-error' : undefined" />
            </div>
            <div class="field">
              <label for="password">Passwort</label>
              <Password input-id="password" v-model="password" name="password" autocomplete="current-password" :feedback="false" toggle-mask required :invalid="!!error" :input-props="{ 'aria-describedby': error ? 'login-error' : undefined }" />
            </div>
            <Button type="submit" label="Anmelden" icon="pi pi-arrow-right" icon-pos="right" :loading="loading" :disabled="oidcLoading" />
            <router-link to="/forgot-password" class="text-link">Passwort vergessen?</router-link>
          </template>
        </form>
        <p class="login-help">Noch keinen Zugang? Wende dich an die Administration deiner Jugendfeuerwehr.</p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { oidcApi } from '@/api/oidc'
import { brandingApi } from '@/api/branding'
import type { OIDCPublicConfig } from '@/types/oidc'
import type { PublicBranding } from '@/types/settings'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { getApiErrorMessage } from '@/utils/apiError'
import { hardNavigate, isServerPath, safeReturnPath } from '@/utils/navigation'
import type { SessionStatus } from '@/api/auth'
import { passkeysSupported } from '@/utils/webauthn'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const oidcConfig = ref<OIDCPublicConfig | null>(null)
const oidcLoading = ref(false)
const showLocalLogin = ref(false)
const branding = ref<PublicBranding | null>(null)
const mfaStep = ref(false)
const mfaCode = ref('')
const useRecoveryCode = ref(false)
const passkeyBusy = ref(false)
const canUsePasskeys = passkeysSupported()
const hasTotp = computed(() => authStore.mfaMethods?.totp ?? true)
const offerPasskey = computed(() => !!authStore.mfaMethods?.passkey && passkeysSupported() && !useRecoveryCode.value)
const showCodeField = computed(() => useRecoveryCode.value || hasTotp.value || !offerPasskey.value)
const mfaDescription = computed(() => {
  if (useRecoveryCode.value) return 'Gib einen deiner Wiederherstellungscodes ein.'
  if (offerPasskey.value && hasTotp.value) return 'Bestätige mit deinem Passkey oder dem Code aus deiner Authenticator-App.'
  if (offerPasskey.value) return 'Bestätige die Anmeldung mit deinem Passkey.'
  return 'Gib den sechsstelligen Code aus deiner Authenticator-App ein.'
})
const info = ref(router.currentRoute.value.query.expired ? 'Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.' : '')

// Optional branding and SSO discovery must not delay local sign-in.
onMounted(() => {
  // Returning from SSO with a pending second factor, or after a reload mid-login.
  if (authStore.mfaPending) mfaStep.value = true
  void oidcApi.getPublicConfig().then(response => { oidcConfig.value = response.data }).catch(() => {})
  void brandingApi.getPublicBranding().then(response => {
    branding.value = response.data
    if (response.data.title) document.title = response.data.title
  }).catch(() => {})
})

function returnPath() {
  return safeReturnPath(router.currentRoute.value.query.next)
}

async function finish(status: SessionStatus) {
  if (status.mfa_required && !status.authenticated) {
    mfaStep.value = true
    return
  }
  const target = status.mfa_setup_required ? '/profile?mfa=setup' : returnPath()
  if (isServerPath(target)) hardNavigate(target)
  else await router.replace(target)
}

function toggleRecoveryCode() {
  useRecoveryCode.value = !useRecoveryCode.value
  mfaCode.value = ''
  error.value = ''
}

async function restartLogin() {
  await authStore.logout()
}

async function handleMfa() {
  if (loading.value || !mfaCode.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    await finish(await authStore.verifyMfa(mfaCode.value.trim()))
  } catch (err) {
    mfaCode.value = ''
    error.value = getApiErrorMessage(err, 'Der Code ist ungültig.')
    // An expired or exhausted attempt has to restart with the password.
    const code = (err as { response?: { data?: { code?: string } } }).response?.data?.code
    if (code === 'mfa_login_expired') mfaStep.value = false
  } finally {
    loading.value = false
  }
}

async function handlePasskey() {
  if (loading.value) return
  loading.value = true
  passkeyBusy.value = true
  error.value = ''
  try {
    await finish(await authStore.verifyMfaPasskey())
  } catch (err) {
    error.value = authStore.error || 'Der Passkey konnte nicht bestätigt werden.'
    const code = (err as { response?: { data?: { code?: string } } }).response?.data?.code
    if (code === 'mfa_login_expired') mfaStep.value = false
  } finally {
    loading.value = false
    passkeyBusy.value = false
  }
}

/** Passkey with PIN or biometrics: no username, password or code needed (SEC-12). */
async function handlePasskeySignIn() {
  if (loading.value || oidcLoading.value) return
  loading.value = true
  passkeyBusy.value = true
  error.value = ''
  info.value = ''
  try {
    await finish(await authStore.signInWithPasskey())
  } catch {
    error.value = authStore.error || 'Die Anmeldung mit Passkey ist fehlgeschlagen.'
  } finally {
    loading.value = false
    passkeyBusy.value = false
  }
}

async function handleOIDCLogin() {
  if (loading.value || oidcLoading.value) return
  oidcLoading.value = true
  error.value = ''
  try {
    await authStore.loginWithOidc(returnPath())
  } catch (err) {
    error.value = getApiErrorMessage(err, 'SSO-Anmeldung fehlgeschlagen.')
    oidcLoading.value = false
  }
}

async function handleLogin() {
  if (loading.value || oidcLoading.value) return
  if (!username.value.trim() || !password.value) {
    error.value = 'Bitte gib Benutzername und Passwort ein.'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const status = await authStore.login(username.value.trim(), password.value)
    password.value = ''
    await finish(status)
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Anmeldung fehlgeschlagen. Bitte überprüfe deine Zugangsdaten.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100dvh; display: grid; grid-template-columns: 1fr 1fr; background: var(--surface-card, #fff); color: var(--text-color, #17212f); }
.login-intro { background: #172534; color: #fff; padding: clamp(2rem, 5vw, 5rem); display: flex; flex-direction: column; justify-content: space-between; gap: 4rem; }
.brand { display: flex; align-items: center; gap: .8rem; font-size: 1.3rem; font-weight: 700; }
.brand img { width: 42px; height: 42px; object-fit: contain; }
.brand > i { display: grid; place-items: center; background: #b42b36; width: 44px; height: 44px; border-radius: 12px; font-size: 1.4rem; }
.eyebrow { font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .12em; color: var(--text-color-secondary, #637080); margin: 0 0 1rem; }
.intro-copy .eyebrow { color: #eaa5ab; }
h1 { font-size: clamp(2.6rem, 4.4vw, 4.7rem); line-height: 1.08; letter-spacing: -.045em; margin: 0 0 1.7rem; }
.intro-copy > p:not(.eyebrow) { max-width: 420px; color: #c5cdd6; line-height: 1.8; font-size: 1.05rem; }
.intro-modules { display: flex; flex-wrap: wrap; gap: 1.25rem; margin-top: 2rem; color: #e6eaf0; font-size: .85rem; }
.intro-modules span { display: flex; align-items: center; gap: .5rem; }
.intro-footer { color: #aab7c5; font-size: .8rem; }
.login-panel { padding: 3rem 2rem; display: grid; place-items: center; }
.login-form-wrap { width: 100%; max-width: 380px; }
h2 { font-size: 2rem; letter-spacing: -.03em; margin: 0 0 .7rem; }
.login-description { color: var(--text-color-secondary); margin: 0 0 2rem; }
.login-form { display: flex; flex-direction: column; gap: 1.25rem; }
.field { display: flex; flex-direction: column; gap: .5rem; }
.field label { font-size: .9rem; font-weight: 600; }
.field :deep(.p-inputtext), .field :deep(.p-password) { width: 100%; }
.field :deep(input), .login-form :deep(.p-button) { min-height: 46px; }
.text-link { color: var(--primary-color, #b42b36); text-align: center; background: transparent; border: 0; font: inherit; font-size: .9rem; cursor: pointer; padding: .4rem; text-decoration: underline; text-underline-offset: 4px; }
.login-help { color: var(--text-color-secondary); font-size: .82rem; line-height: 1.7; margin-top: 2.5rem; }
.divider { display: flex; align-items: center; gap: 1rem; color: var(--text-color-secondary); font-size: .8rem; }
.divider::before, .divider::after { content: ''; height: 1px; background: var(--surface-border, #ddd); flex: 1; }
@media (max-width: 760px) { .login-page { grid-template-columns: 1fr; } .login-intro { padding: 1.5rem; gap: 0; } .intro-copy, .intro-footer { display: none; } .login-panel { padding: 2.5rem 1.5rem; align-items: start; } }
</style>
