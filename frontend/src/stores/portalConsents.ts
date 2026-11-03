/** Portal: parents grant and withdraw consents for each child. */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { portalApi } from '@/api/portal'
import type { ConsentStatus, PortalConsentOverview } from '@/types/privacy'
import { getApiErrorMessage } from '@/utils/apiError'

export const usePortalConsentsStore = defineStore('portalConsents', () => {
  const overview = ref<PortalConsentOverview>({ kinds: [], people: [] })
  const loading = ref(false)
  const error = ref<string | null>(null)
  /** ``member:kind`` of the change in flight. */
  const saving = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      overview.value = (await portalApi.consents()).data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Die Einwilligungen konnten nicht geladen werden.')
    } finally {
      loading.value = false
    }
  }

  async function change(member: number, kind: string, status: ConsentStatus) {
    saving.value = `${member}:${kind}`
    error.value = null
    try {
      overview.value = (await portalApi.changeConsent({ member, kind, status })).data
      return true
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Die Einwilligung konnte nicht gespeichert werden.')
      return false
    } finally {
      saving.value = null
    }
  }

  return { overview, loading, error, saving, load, change }
})
