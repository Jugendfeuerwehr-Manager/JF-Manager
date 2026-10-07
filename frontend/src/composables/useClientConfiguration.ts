import { reactive } from 'vue'
import apiClient from '@/api'

// Safe organisation-wide defaults, with no credentials or personal data.
const configuration = reactive({
  member_label: 'Mitglieder', service_label: 'Dienstbuch', training_label: 'Ausbildung',
  training_start_time: '18:00', training_end_time: '20:00', default_block_duration_minutes: 15,
})
export function useClientConfiguration() {
  async function refresh() {
    const { data } = await apiClient.get<Partial<typeof configuration>>('/settings/client-defaults/')
    for (const key of Object.keys(configuration) as (keyof typeof configuration)[]) {
      const value = data[key]
      if (typeof value === typeof configuration[key]) Object.assign(configuration, { [key]: value })
    }
  }
  return { configuration, refresh }
}
