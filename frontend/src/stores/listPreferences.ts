import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listPreferencesApi } from '@/api/listPreferences'
import type { ListPreferenceData, ListPreferenceView } from '@/types/listPreferences'

export const useListPreferencesStore = defineStore('listPreferences', () => {
  const saveError = ref(false)

  /** Saved settings, or none when nothing is stored or loading fails (the list still works). */
  async function load(view: ListPreferenceView, department: number | null): Promise<ListPreferenceData> {
    try {
      return (await listPreferencesApi.get(view, department)).data.data ?? {}
    } catch {
      return {}
    }
  }

  async function save(view: ListPreferenceView, department: number | null, data: ListPreferenceData) {
    try {
      await listPreferencesApi.save(view, department, data)
      saveError.value = false
    } catch {
      saveError.value = true
    }
  }

  return { saveError, load, save }
})
