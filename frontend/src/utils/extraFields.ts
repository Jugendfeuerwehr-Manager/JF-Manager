import type { ExtraFieldValue, Member, MemberFieldDefinition } from '@/types/members'

/** Department ids of a member from the list (``department_ids``) or detail (``departments``) shape. */
export function memberDepartmentIds(member: Pick<Member, 'department_ids' | 'departments'>): number[] {
  return member.department_ids ?? member.departments ?? []
}

/** Readable value of an additional member field. */
export function extraFieldText(definition: MemberFieldDefinition, value: ExtraFieldValue | undefined): string {
  if (definition.field_type === 'checkbox') return value === true ? 'Ja' : 'Nein'
  if (value === undefined || value === '') return '–'
  if (definition.field_type === 'date' && typeof value === 'string') {
    return new Date(`${value}T00:00:00`).toLocaleDateString('de-DE')
  }
  return String(value)
}
