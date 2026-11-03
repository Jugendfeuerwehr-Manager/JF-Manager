import type { ExtraFieldValue, MemberFieldDefinition } from '@/types/members'

/** Readable value of an additional member field. */
export function extraFieldText(definition: MemberFieldDefinition, value: ExtraFieldValue | undefined): string {
  if (definition.field_type === 'checkbox') return value === true ? 'Ja' : 'Nein'
  if (value === undefined || value === '') return '–'
  if (definition.field_type === 'date' && typeof value === 'string') {
    return new Date(`${value}T00:00:00`).toLocaleDateString('de-DE')
  }
  return String(value)
}
