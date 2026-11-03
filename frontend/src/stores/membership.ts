import { defineStore } from 'pinia'
import { ref } from 'vue'
import { membershipApi } from '@/api/membership'
import type { MembershipEvent, MembershipEventCorrection } from '@/types/membership'
import { getApiErrorMessage } from '@/utils/apiError'

export const useMembershipStore = defineStore('membership', () => {
  const events = ref<MembershipEvent[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchMemberEvents(memberId: number) {
    loading.value = true
    error.value = null
    try {
      events.value = (await membershipApi.listEvents({ member: memberId, limit: 200 })).data.results
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Mitgliedschaftsverlauf konnte nicht geladen werden')
    } finally {
      loading.value = false
    }
  }

  async function correctEvent(id: number, data: MembershipEventCorrection) {
    error.value = null
    try {
      const updated = (await membershipApi.correctEvent(id, data)).data
      events.value = events.value.map((event) => (event.id === id ? updated : event))
      return updated
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Eintrag konnte nicht korrigiert werden')
      throw e
    }
  }

  function reset() {
    events.value = []
    error.value = null
  }

  return { events, loading, error, fetchMemberEvents, correctEvent, reset }
})
