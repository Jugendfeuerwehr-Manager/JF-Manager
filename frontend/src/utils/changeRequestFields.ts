import type { ChangeRequest, ChangeTarget } from '@/types/changeRequests'

export interface RequestableField {
  field: string
  label: string
  /** Key in the contact block the portal API delivers. */
  key: string
  type: 'text' | 'email' | 'tel'
  autocomplete: string
  half?: boolean
}

const NAME: RequestableField[] = [
  { field: 'name', label: 'Vorname', key: 'first_name', type: 'text', autocomplete: 'given-name' },
  { field: 'lastname', label: 'Nachname', key: 'last_name', type: 'text', autocomplete: 'family-name' },
]
const ADDRESS: RequestableField[] = [
  { field: 'street', label: 'Straße', key: 'street', type: 'text', autocomplete: 'street-address' },
  { field: 'zip_code', label: 'PLZ', key: 'zip_code', type: 'text', autocomplete: 'postal-code', half: true },
  { field: 'city', label: 'Ort', key: 'city', type: 'text', autocomplete: 'address-level2', half: true },
]
const PHONE: RequestableField[] = [
  { field: 'phone', label: 'Telefon', key: 'phone', type: 'tel', autocomplete: 'tel' },
  { field: 'mobile', label: 'Mobil', key: 'mobile', type: 'tel', autocomplete: 'tel' },
]

export const MEMBER_FIELDS: RequestableField[] = [
  ...NAME, ...ADDRESS, ...PHONE,
  { field: 'email', label: 'E-Mail', key: 'email', type: 'email', autocomplete: 'email' },
]
export const PARENT_FIELDS: RequestableField[] = [
  ...NAME, ...ADDRESS, ...PHONE,
  { field: 'email', label: 'E-Mail 1', key: 'email', type: 'email', autocomplete: 'email' },
  { field: 'email2', label: 'E-Mail 2', key: 'email2', type: 'email', autocomplete: 'email' },
]

export const fieldsFor = (target: ChangeTarget) => (target.kind === 'parent' ? PARENT_FIELDS : MEMBER_FIELDS)

export const matchesTarget = (request: ChangeRequest, target: ChangeTarget) =>
  request.kind === target.kind && (target.kind === 'parent' || request.target_id === target.id)

export const requestDate = (iso: string) => {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' }).format(d)
}
export const requestDateTime = (iso: string | null) => {
  const d = iso ? new Date(iso) : null
  return d && !Number.isNaN(d.getTime())
    ? new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(d)
    : ''
}
