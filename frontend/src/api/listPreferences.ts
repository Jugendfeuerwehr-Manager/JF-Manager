import apiClient from './index'
import type { ListPreference, ListPreferenceData, ListPreferenceView } from '@/types/listPreferences'

/** Own saved list filters per view and department (UX-02.3); never search texts. */
export const listPreferencesApi = {
  get(view: ListPreferenceView, department: number | null) {
    return apiClient.get<ListPreference>('/list-preferences/', { params: { view, department: department ?? undefined } })
  },

  save(view: ListPreferenceView, department: number | null, data: ListPreferenceData) {
    return apiClient.post<ListPreference>('/list-preferences/', { view, department, data })
  },
}
