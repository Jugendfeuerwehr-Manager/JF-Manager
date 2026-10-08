import { onMounted, onUnmounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { authApi } from '@/api/auth'
import { userApi } from '@/api/user'
import { useAuthStore } from '@/stores/auth'

const CHECK_INTERVAL = 60_000
const WARN_BEFORE = 2 * 60_000

/**
 * Announces the end of the server session in advance. Status checks do not
 * count as activity, so polling never keeps an unattended session alive.
 */
export function useSessionTimeout() {
  const auth = useAuthStore()
  const confirm = useConfirm()
  const toast = useToast()
  let timer: ReturnType<typeof setInterval> | undefined
  let idleWarned = false
  let absoluteWarned = false

  function stayActive() {
    idleWarned = false
    // Any authenticated request counts as activity.
    void userApi.me().then(check).catch(() => {})
  }

  async function check() {
    if (!auth.isAuthenticated) return
    let status
    try {
      status = (await authApi.session()).data
    } catch {
      return // Offline: keep the current view; the next request reports problems.
    }
    if (!status.authenticated) {
      auth.handleSessionExpired()
      return
    }
    auth.session = status
    const now = Date.now()
    const absoluteLeft = status.absolute_expires_at ? Date.parse(status.absolute_expires_at) - now : Infinity
    const idleLeft = status.idle_expires_at ? Date.parse(status.idle_expires_at) - now : Infinity
    if (absoluteLeft <= WARN_BEFORE && !absoluteWarned) {
      absoluteWarned = true
      toast.add({
        severity: 'warn',
        summary: 'Sitzung endet bald',
        detail: 'Die maximale Sitzungsdauer ist erreicht. Bitte speichere offene Änderungen; danach ist eine neue Anmeldung nötig.',
        life: 30_000,
      })
    } else if (idleLeft <= WARN_BEFORE && absoluteLeft > idleLeft && !idleWarned) {
      idleWarned = true
      confirm.require({
        group: 'session-timeout',
        header: 'Sitzung läuft ab',
        message: 'Du warst eine Weile inaktiv und wirst in Kürze automatisch abgemeldet.',
        icon: 'pi pi-clock',
        acceptLabel: 'Angemeldet bleiben',
        rejectLabel: 'Abmelden',
        accept: stayActive,
        reject: () => void auth.logout(),
      })
    } else if (idleLeft > WARN_BEFORE) {
      idleWarned = false
    }
  }

  onMounted(() => {
    timer = setInterval(() => void check(), CHECK_INTERVAL)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })
}
