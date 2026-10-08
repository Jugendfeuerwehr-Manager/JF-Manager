import { defineStore } from 'pinia'
import { ref } from 'vue'
import { portalApi, type PortalMe } from '@/api/portal'
import { getApiErrorMessage } from '@/utils/apiError'

export const usePortalStore = defineStore('portal', () => {
  const me = ref<PortalMe | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchMe() {
    loading.value = true
    error.value = null
    try {
      me.value = (await portalApi.me()).data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Die Daten konnten nicht geladen werden.')
    } finally {
      loading.value = false
    }
  }

  return { me, loading, error, fetchMe }
})
