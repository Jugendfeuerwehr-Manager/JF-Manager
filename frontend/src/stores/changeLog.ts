import { defineStore } from 'pinia'
import { ref } from 'vue'
import { changeLogApi } from '@/api/changeLog'
import type { ChangeLogEntry } from '@/types/changeLog'
import { classifyApiError, type ApiErrorKind } from '@/utils/apiError'

/** Change history of one record (member detail). */
export const useChangeLogStore = defineStore('changeLog', () => {
  const entries = ref<ChangeLogEntry[]>([])
  const loading = ref(false)
  const error = ref<ApiErrorKind | null>(null)
  let seq = 0

  async function load(kind: 'member' | 'parent', id: number) {
    const current = ++seq
    loading.value = true
    error.value = null
    try {
      const { data } = await changeLogApi.forRecord(kind, id)
      if (current === seq) entries.value = data.results
    } catch (err) {
      if (current === seq) {
        entries.value = []
        error.value = classifyApiError(err)
      }
    } finally {
      if (current === seq) loading.value = false
    }
  }

  return { entries, loading, error, load }
})
