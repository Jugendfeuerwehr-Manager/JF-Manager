import { computed, onMounted, onScopeDispose, ref, watch } from 'vue'
import apiClient from '@/api'
import { useDepartmentsStore } from '@/stores/departments'
import { getApiErrorMessage } from '@/utils/apiError'

export interface RoleMemberOption { id: number; full_name: string; department_ids: number[] }
export function useRoleMemberOptions(purpose: 'inventory' | 'orders') {
  const departments = useDepartmentsStore()
  const members = ref<RoleMemberOption[]>([])
  const error = ref('')
  let generation = 0
  async function load() {
    const requestId = ++generation
    const selectedDepartment = departments.activeDepartmentId
    members.value = []; error.value = ''
    try {
      const rows: RoleMemberOption[] = []
      let offset = 0
      while (true) {
        const { data } = await apiClient.get<{ results: RoleMemberOption[]; next: string | null }>('/role-member-options/', {
          params: { purpose, limit: 100, offset, department: selectedDepartment },
        })
        if (requestId !== generation) return
        rows.push(...data.results)
        if (!data.next || !data.results.length) break
        offset += data.results.length
      }
      if (requestId === generation) members.value = rows
    } catch (err) {
      if (requestId === generation) error.value = getApiErrorMessage(err, 'Personenauswahl konnte nicht geladen werden.')
    }
  }
  watch(() => departments.activeDepartmentId, load)
  onMounted(load)
  onScopeDispose(() => { generation++ })
  return { members, error, load, memberOptions: computed(() => members.value.map(member => ({ value: member.id, label: member.full_name }))) }
}
