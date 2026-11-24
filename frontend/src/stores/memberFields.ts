import { defineStore } from 'pinia'
import { ref } from 'vue'
import { memberFieldsApi } from '@/api/memberFields'
import type { MemberFieldDefinition, MemberFieldDefinitionInput } from '@/types/members'
import { getApiErrorMessage } from '@/utils/apiError'

export const useMemberFieldsStore = defineStore('memberFields', () => {
  const definitions = ref<MemberFieldDefinition[]>([])
  const loaded = ref(false)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  async function fetchDefinitions() {
    loading.value = true
    error.value = null
    try {
      definitions.value = (await memberFieldsApi.list()).data.results
      loaded.value = true
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Zusatzfelder konnten nicht geladen werden')
    } finally {
      loading.value = false
    }
  }

  async function ensureLoaded() {
    if (!loaded.value && !loading.value) await fetchDefinitions()
  }

  /** Active fields that apply to members of ``departmentIds`` (plus the organisation's). */
  function applicableTo(departmentIds: number[]) {
    return definitions.value.filter(
      (definition) =>
        definition.active && (definition.department === null || departmentIds.includes(definition.department))
    )
  }

  async function save(data: Partial<MemberFieldDefinitionInput>, id?: number) {
    saving.value = true
    error.value = null
    try {
      const saved = id
        ? (await memberFieldsApi.update(id, data)).data
        : (await memberFieldsApi.create(data as MemberFieldDefinitionInput)).data
      definitions.value = id
        ? definitions.value.map((definition) => (definition.id === id ? saved : definition))
        : [...definitions.value, saved]
      return saved
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Zusatzfeld konnte nicht gespeichert werden')
      throw e
    } finally {
      saving.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  async function remove(id: number) {
    error.value = null
    try {
      await memberFieldsApi.remove(id)
      definitions.value = definitions.value.filter((definition) => definition.id !== id)
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Zusatzfeld konnte nicht gelöscht werden')
      throw e
    }
  }

  return {
    definitions,
    loaded,
    loading,
    saving,
    error,
    fetchDefinitions,
    ensureLoaded,
    applicableTo,
    save,
    clearError,
    remove
  }
})
