import { ref, watch, type Ref } from 'vue'
import { membersApi } from '@/api/members'
import type { Member } from '@/types/members'

export interface PossibleDuplicate {
  id: number
  name: string
}

const normalize = (value: string) => value.trim().toLocaleLowerCase('de-DE')

function isoDate(value: Date): string {
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${value.getFullYear()}-${month}-${day}`
}

/**
 * UX-02.2: warn before creating a member who already exists (same first name, last name and birthday).
 * Uses the normal, department-scoped member list, so only members the user may see are suggested.
 * The check never blocks saving; twins or a new record on purpose stay possible.
 */
export function useMemberDuplicates(
  firstName: Ref<string>,
  lastName: Ref<string>,
  birthday: Ref<Date | null>,
  enabled: Ref<boolean>,
  delayMs = 400
) {
  const duplicates = ref<PossibleDuplicate[]>([])
  let timer: ReturnType<typeof setTimeout> | null = null
  let request = 0

  async function check() {
    const first = normalize(firstName.value)
    const last = normalize(lastName.value)
    if (!enabled.value || !first || !last || !birthday.value) {
      duplicates.value = []
      return
    }
    const current = ++request
    try {
      const response = await membersApi.list({ search: lastName.value.trim(), birthday: isoDate(birthday.value), limit: 10 })
      if (current !== request) return
      duplicates.value = response.data.results
        .filter((member: Member) => normalize(member.name) === first && normalize(member.lastname) === last)
        .map((member: Member) => ({ id: member.id, name: member.full_name }))
    } catch {
      // A failed hint must not block the form; the server still validates on save.
      if (current === request) duplicates.value = []
    }
  }

  watch([firstName, lastName, birthday, enabled], () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(check, delayMs)
  })

  return { duplicates, check }
}
