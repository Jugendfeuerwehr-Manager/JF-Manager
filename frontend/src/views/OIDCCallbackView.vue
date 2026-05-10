<template>
  <div class="oidc-callback">
    <!-- Loading state -->
    <div v-if="loading" class="callback-state">
      <ProgressSpinner />
      <p>Anmeldung wird verarbeitet…</p>
    </div>

    <!-- Error state -->
    <div v-else-if="errorMessage" class="callback-state callback-error">
      <i class="pi pi-times-circle error-icon"></i>
      <h2>Anmeldung fehlgeschlagen</h2>
      <p>{{ errorMessage }}</p>

      <!-- Debug details (toggle) -->
      <div v-if="debugInfo" class="debug-section">
        <button class="debug-toggle" @click="debugExpanded = !debugExpanded">
          <i :class="debugExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" />
          {{ debugExpanded ? 'Details ausblenden' : 'Details anzeigen' }}
        </button>
        <div v-if="debugExpanded" class="debug-body">
          <div class="debug-row">
            <span class="debug-label">E-Mail</span>
            <span class="debug-value">{{ debugInfo.email || '–' }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-label">Name</span>
            <span class="debug-value">{{ debugInfo.name || '–' }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-label">Sub (Benutzer-ID)</span>
            <span class="debug-value debug-mono">{{ debugInfo.sub || '–' }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-label">Issuer</span>
            <span class="debug-value debug-mono">{{ debugInfo.issuer || '–' }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-label">Gruppen-Claim ({{ debugInfo.groups_claim || 'groups' }})</span>
            <span class="debug-value">
              <span v-if="debugInfo.groups?.length">
                <code v-for="g in debugInfo.groups" :key="g" class="debug-tag">{{ g }}</code>
              </span>
              <span v-else class="debug-empty">Keine Gruppen im Token</span>
            </span>
          </div>
        </div>
      </div>

      <Button label="Zurück zum Login" icon="pi pi-arrow-left" @click="goToLogin" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { oidcApi } from '@/api/oidc'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { getApiErrorMessage } from '@/utils/apiError'

interface OIDCDebugInfo {
  email: string
  name: string
  sub: string
  issuer: string
  groups_claim: string
  groups: string[]
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const errorMessage = ref('')
const debugInfo = ref<OIDCDebugInfo | null>(null)
const debugExpanded = ref(false)

function goToLogin() {
  router.push('/login')
}

onMounted(async () => {
  // IdP returned an error
  const errorParam = route.query.error as string | undefined
  if (errorParam) {
    loading.value = false
    errorMessage.value = errorParam || 'Unbekannter Fehler beim SSO-Login.'
    const debugParam = route.query.debug as string | undefined
    if (debugParam) {
      try {
        debugInfo.value = JSON.parse(debugParam) as OIDCDebugInfo
      } catch {
        // ignore parse errors
      }
    }
    return
  }

  const exchangeCode = route.query.exchange_code as string | undefined
  if (!exchangeCode) {
    loading.value = false
    errorMessage.value = 'Ungültige OIDC-Antwort: exchange_code fehlt.'
    return
  }

  try {
    const response = await oidcApi.exchangeCode({ exchange_code: exchangeCode })
    await authStore.setOIDCTokens(response.data.access, response.data.refresh)

    // Navigate to the originally intended page or the one returned by backend
    const returnUrl = sessionStorage.getItem('oidc_return_url') || response.data.next || '/'
    sessionStorage.removeItem('oidc_return_url')

    // Avoid redirecting back to login or oidc callback pages
    const safeUrl = ['/login', '/auth/oidc/callback'].some((p) => returnUrl.startsWith(p)) ? '/' : returnUrl
    router.replace(safeUrl)
  } catch (err) {
    loading.value = false
    errorMessage.value = getApiErrorMessage(err, 'SSO-Anmeldung fehlgeschlagen. Bitte versuche es erneut.')
  }
})
</script>

<style scoped>
.oidc-callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #c31432 0%, #e74c3c 50%, #c31432 100%);
}

.callback-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  color: white;
  text-align: center;
  max-width: 480px;
  width: 90vw;
}

.callback-error .error-icon {
  font-size: 3rem;
  color: #ffd700;
}

.callback-error h2 {
  margin: 0;
  font-size: 1.5rem;
}

.callback-error p {
  margin: 0;
  opacity: 0.9;
}

/* Debug section */
.debug-section {
  width: 100%;
  text-align: left;
}

.debug-toggle {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.5rem;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  padding: 0.4rem 0.75rem;
  width: 100%;
  justify-content: center;
}

.debug-toggle:hover {
  background: rgba(255, 255, 255, 0.25);
}

.debug-body {
  background: rgba(0, 0, 0, 0.25);
  border-radius: 0 0 0.5rem 0.5rem;
  font-size: 0.8rem;
  margin-top: 0.25rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.debug-row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.debug-label {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.debug-value {
  color: white;
  word-break: break-all;
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.debug-mono {
  font-family: monospace;
}

.debug-tag {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.25rem;
  font-family: monospace;
  padding: 0.1rem 0.4rem;
}

.debug-empty {
  color: rgba(255, 255, 255, 0.5);
  font-style: italic;
}
</style>
