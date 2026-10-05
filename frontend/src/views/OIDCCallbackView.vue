<template>
  <div class="oidc-callback">
    <!-- Loading state -->
    <div v-if="loading" class="callback-state" role="status">
      <ProgressSpinner />
      <p>Anmeldung wird verarbeitet…</p>
    </div>

    <!-- Error state -->
    <div v-else-if="errorMessage" class="callback-state callback-error" role="alert">
      <i class="pi pi-times-circle error-icon" aria-hidden="true"></i>
      <h2>Anmeldung fehlgeschlagen</h2>
      <p>{{ errorMessage }}</p>
      <p class="hint">Details stehen für Administratoren im Serverprotokoll.</p>
      <Button label="Zurück zum Login" icon="pi pi-arrow-left" @click="goToLogin" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { hardNavigate, isServerPath, safeReturnPath } from '@/utils/navigation'

// The backend only sends these fixed codes; never personal data or exception texts.
const ERROR_MESSAGES: Record<string, string> = {
  provider_error: 'Der Identity Provider hat die Anmeldung abgebrochen.',
  invalid_response: 'Ungültige Antwort des Identity Providers.',
  expired: 'Die Anmeldung ist abgelaufen oder wurde in einem anderen Browser gestartet. Bitte erneut anmelden.',
  disabled: 'SSO ist deaktiviert.',
  unavailable: 'Der Identity Provider ist derzeit nicht erreichbar.',
  verification_failed: 'Die Anmeldung konnte nicht bestätigt werden.',
  account_rejected: 'Für dieses Konto ist keine Anmeldung möglich. Bitte wende dich an die Administration.',
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const errorMessage = ref('')

function goToLogin() {
  router.push('/login')
}

onMounted(async () => {
  const errorCode = typeof route.query.error === 'string' ? route.query.error : ''
  if (errorCode) {
    loading.value = false
    errorMessage.value = ERROR_MESSAGES[errorCode] ?? 'Die SSO-Anmeldung ist fehlgeschlagen.'
    return
  }

  const next = safeReturnPath(route.query.next)
  try {
    const status = await authStore.refreshSession()
    if (status.mfa_required && !status.authenticated) {
      await router.replace({ path: '/login', query: { next } })
    } else if (!status.authenticated) {
      throw new Error('not authenticated')
    } else if (status.mfa_setup_required) {
      await router.replace({ path: '/profile', query: { mfa: 'setup' } })
    } else if (isServerPath(next)) {
      hardNavigate(next)
    } else {
      await router.replace(next.startsWith('/auth/oidc/callback') ? '/' : next)
    }
  } catch {
    loading.value = false
    errorMessage.value = 'Die SSO-Anmeldung ist fehlgeschlagen. Bitte versuche es erneut.'
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

.callback-error .hint {
  font-size: 0.85rem;
  opacity: 0.75;
}
</style>
