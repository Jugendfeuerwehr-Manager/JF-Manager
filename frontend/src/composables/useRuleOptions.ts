import { computed, ref } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import { useGroupsStore } from '@/stores/groups'
import { useMembersStore } from '@/stores/members'
import { useDepartmentsStore } from '@/stores/departments'
import type { ValueKind } from '@/api/participation'

export interface RuleOption { value: number | string, label: string }

export const GENDER_OPTIONS: RuleOption[] = [
  { value: 'male', label: 'männlich' },
  { value: 'female', label: 'weiblich' },
  { value: 'diverse', label: 'divers' },
]

/** Option lists for the rule rows, taken from the stores that already own them. */
export function useRuleOptions() {
  const qualifications = useQualificationsStore()
  const groups = useGroupsStore()
  const members = useMembersStore()
  const departments = useDepartmentsStore()
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      await Promise.all([
        qualifications.fetchQualificationTypes(),
        qualifications.fetchSpecialTaskTypes(),
        groups.fetchGroups(),
        members.fetchStatuses(),
        departments.fetchDepartments(),
      ])
    } catch {
      error.value = 'Auswahllisten konnten nicht vollständig geladen werden.'
    } finally {
      loading.value = false
    }
  }

  const options = computed<Record<ValueKind, RuleOption[]>>(() => {
    const named = (list: Array<{ id: number, name: string }>) => list.map(item => ({ value: item.id, label: item.name }))
    return {
      qualification: named(qualifications.qualificationTypes),
      special_task: named(qualifications.specialTaskTypes),
      gender: GENDER_OPTIONS,
      group: named(groups.groups),
      status: named(members.statuses),
      department: named(departments.departments),
    }
  })

  return { options, loading, error, load }
}
