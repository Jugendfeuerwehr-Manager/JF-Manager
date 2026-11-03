/**
 * Pure helpers for application form schemas. Every change returns a new schema so the
 * builder store can keep an undo history.
 */
import type {
  ElementLocation,
  ElementType,
  FormElement,
  FormSchema,
  SchemaIssue,
  VisibilityRule
} from '@/types/admissions'

export interface PaletteEntry {
  type: ElementType
  label: string
  icon: string
  group: 'Eingabe' | 'Inhalt' | 'Rechtliches' | 'Personen'
}

export const PALETTE: PaletteEntry[] = [
  { type: 'text', label: 'Textfeld', icon: 'pi pi-pencil', group: 'Eingabe' },
  { type: 'textarea', label: 'Mehrzeiliger Text', icon: 'pi pi-align-left', group: 'Eingabe' },
  { type: 'date', label: 'Datum', icon: 'pi pi-calendar', group: 'Eingabe' },
  { type: 'email', label: 'E-Mail', icon: 'pi pi-envelope', group: 'Eingabe' },
  { type: 'phone', label: 'Telefon', icon: 'pi pi-phone', group: 'Eingabe' },
  { type: 'select', label: 'Auswahlliste', icon: 'pi pi-list', group: 'Eingabe' },
  { type: 'radio', label: 'Einfachauswahl', icon: 'pi pi-circle', group: 'Eingabe' },
  { type: 'checkbox', label: 'Ankreuzfeld', icon: 'pi pi-check-square', group: 'Eingabe' },
  { type: 'photo', label: 'Passbild', icon: 'pi pi-image', group: 'Eingabe' },
  { type: 'heading', label: 'Überschrift', icon: 'pi pi-bookmark', group: 'Inhalt' },
  { type: 'richtext', label: 'Text / Erklärung', icon: 'pi pi-file', group: 'Inhalt' },
  { type: 'divider', label: 'Trennlinie', icon: 'pi pi-minus', group: 'Inhalt' },
  { type: 'legal_ack', label: 'Rechtstext bestätigen', icon: 'pi pi-shield', group: 'Rechtliches' },
  { type: 'consent', label: 'Einwilligung', icon: 'pi pi-verified', group: 'Rechtliches' },
  { type: 'signature', label: 'Unterschrift', icon: 'pi pi-pen-to-square', group: 'Rechtliches' },
  { type: 'guardians', label: 'Sorgeberechtigte', icon: 'pi pi-users', group: 'Personen' }
]

export const ELEMENT_LABELS: Record<ElementType, string> = Object.fromEntries(
  PALETTE.map((entry) => [entry.type, entry.label])
) as Record<ElementType, string>

const CONTENT_TYPES: ElementType[] = ['heading', 'richtext', 'divider']

export function isContent(type: ElementType) {
  return CONTENT_TYPES.includes(type)
}

export function newId(prefix = 'e') {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

export function allElements(schema: FormSchema): FormElement[] {
  return schema.pages.flatMap((page) => page.sections.flatMap((section) => section.elements))
}

function uniqueKey(base: string, schema: FormSchema) {
  const taken = new Set(allElements(schema).map((element) => element.key).filter(Boolean))
  if (!taken.has(base)) return base
  let counter = 2
  while (taken.has(`${base}_${counter}`)) counter++
  return `${base}_${counter}`
}

export function createElement(type: ElementType, schema: FormSchema): FormElement {
  const id = newId()
  if (isContent(type)) {
    if (type === 'heading') return { id, type, label: 'Überschrift' }
    if (type === 'richtext') return { id, type, html: '<p>Erklärender Text</p>' }
    return { id, type }
  }
  const base: FormElement = { id, type, key: uniqueKey(type, schema), label: ELEMENT_LABELS[type], required: false }
  if (type === 'select' || type === 'radio') {
    return { ...base, options: [{ value: 'ja', label: 'Ja' }, { value: 'nein', label: 'Nein' }] }
  }
  if (type === 'photo') return { ...base, target: 'member.avatar' }
  if (type === 'legal_ack') return { ...base, label: 'Ich habe die Datenschutzhinweise gelesen.', legal_kind: 'privacy', required: true }
  if (type === 'consent') return { ...base, consent_kind: '', person: 'applicant' }
  if (type === 'signature') return { ...base, role: 'applicant', required: true }
  if (type === 'guardians') {
    return {
      ...base,
      key: uniqueKey('sorgeberechtigte', schema),
      min: 1,
      max: 2,
      fields: [
        { target: 'guardian.name', required: true },
        { target: 'guardian.lastname', required: true },
        { target: 'guardian.mobile', required: true },
        { target: 'guardian.email', required: true }
      ],
      visible_if: { age_below: 18 }
    }
  }
  return base
}

/** Deep copy; works on Vue's reactive proxies too (the schema is plain JSON). */
export function cloneSchema<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function clone(schema: FormSchema): FormSchema {
  return cloneSchema(schema)
}

export function locate(schema: FormSchema, elementId: string): ElementLocation | null {
  for (const [page, p] of schema.pages.entries()) {
    for (const [section, s] of p.sections.entries()) {
      const index = s.elements.findIndex((element) => element.id === elementId)
      if (index !== -1) return { page, section, index }
    }
  }
  return null
}

export function insertElement(schema: FormSchema, at: ElementLocation, element: FormElement): FormSchema {
  const next = clone(schema)
  const elements = next.pages[at.page]?.sections[at.section]?.elements
  if (!elements) return schema
  elements.splice(Math.min(at.index, elements.length), 0, element)
  return next
}

export function moveElement(schema: FormSchema, from: ElementLocation, to: ElementLocation): FormSchema {
  const next = clone(schema)
  const source = next.pages[from.page]?.sections[from.section]?.elements
  const target = next.pages[to.page]?.sections[to.section]?.elements
  if (!source || !target) return schema
  const [moved] = source.splice(from.index, 1)
  if (!moved) return schema
  // Removing first shifts later positions in the same list by one.
  const sameList = from.page === to.page && from.section === to.section
  const index = sameList && to.index > from.index ? to.index - 1 : to.index
  target.splice(Math.min(index, target.length), 0, moved)
  return next
}

export function removeElement(schema: FormSchema, at: ElementLocation): FormSchema {
  const next = clone(schema)
  next.pages[at.page]?.sections[at.section]?.elements.splice(at.index, 1)
  return next
}

export function updateElement(schema: FormSchema, elementId: string, patch: Partial<FormElement>): FormSchema {
  const at = locate(schema, elementId)
  if (!at) return schema
  const next = clone(schema)
  const elements = next.pages[at.page]!.sections[at.section]!.elements
  elements[at.index] = { ...elements[at.index]!, ...patch }
  return next
}

export function addPage(schema: FormSchema, title = 'Neue Seite'): FormSchema {
  const next = clone(schema)
  next.pages.push({ id: newId('p'), title, sections: [{ id: newId('s'), title: 'Abschnitt', elements: [] }] })
  return next
}

export function addSection(schema: FormSchema, page: number, title = 'Neuer Abschnitt'): FormSchema {
  const next = clone(schema)
  next.pages[page]?.sections.push({ id: newId('s'), title, elements: [] })
  return next
}

export function renameContainer(schema: FormSchema, page: number, section: number | null, title: string): FormSchema {
  const next = clone(schema)
  const target = section === null ? next.pages[page] : next.pages[page]?.sections[section]
  if (target) target.title = title
  return next
}

export function removeContainer(schema: FormSchema, page: number, section: number | null): FormSchema {
  const next = clone(schema)
  if (section === null) next.pages.splice(page, 1)
  else next.pages[page]?.sections.splice(section, 1)
  return next
}

export function movePage(schema: FormSchema, from: number, to: number): FormSchema {
  if (to < 0 || to >= schema.pages.length) return schema
  const next = clone(schema)
  const [page] = next.pages.splice(from, 1)
  if (page) next.pages.splice(to, 0, page)
  return next
}

export function elementPath(at: ElementLocation) {
  return `pages.${at.page}.sections.${at.section}.elements.${at.index}`
}

export function issuesByElement(schema: FormSchema, issues: SchemaIssue[]): Map<string, string[]> {
  const result = new Map<string, string[]>()
  for (const [page, p] of schema.pages.entries()) {
    for (const [section, s] of p.sections.entries()) {
      for (const [index, element] of s.elements.entries()) {
        const path = elementPath({ page, section, index })
        const messages = issues.filter((issue) => issue.path === path).map((issue) => issue.message)
        if (messages.length) result.set(element.id, messages)
      }
    }
  }
  return result
}

/** Age in full years on ``day``; null without a birthday. */
export function ageOn(birthday: string | null | undefined, day: Date = new Date()): number | null {
  if (!birthday) return null
  const born = new Date(`${birthday}T00:00:00`)
  if (Number.isNaN(born.getTime())) return null
  let age = day.getFullYear() - born.getFullYear()
  const beforeBirthday =
    day.getMonth() < born.getMonth() || (day.getMonth() === born.getMonth() && day.getDate() < born.getDate())
  if (beforeBirthday) age--
  return age
}

/** Whether an element is shown for the current answers (mirrors the backend). */
export function isVisible(
  rule: VisibilityRule | null | undefined,
  answers: Record<string, unknown>,
  age: number | null
): boolean {
  if (!rule) return true
  if ('age_below' in rule) return age === null || age < rule.age_below
  return answers[rule.field] === rule.equals
}

export const GENDER_OPTIONS = [
  { value: 'male', label: 'Männlich' },
  { value: 'female', label: 'Weiblich' },
  { value: 'diverse', label: 'Divers' }
]

export const GUARDIAN_FIELD_META: Record<string, { label: string; input: 'text' | 'email' | 'tel' }> = {
  'guardian.name': { label: 'Vorname', input: 'text' },
  'guardian.lastname': { label: 'Nachname', input: 'text' },
  'guardian.street': { label: 'Straße, Hausnr.', input: 'text' },
  'guardian.zip_code': { label: 'PLZ', input: 'text' },
  'guardian.city': { label: 'Ort', input: 'text' },
  'guardian.phone': { label: 'Telefon', input: 'tel' },
  'guardian.mobile': { label: 'Mobil', input: 'tel' },
  'guardian.email': { label: 'E-Mail-Adresse', input: 'email' },
  'guardian.email2': { label: 'Zweite E-Mail-Adresse', input: 'email' }
}

export const SIGNATURE_ROLE_LABELS = {
  applicant: 'Antragsteller*in',
  guardian_1: '1. Erziehungsberechtigte*r',
  guardian_2: '2. Erziehungsberechtigte*r'
} as const

/** Guardian answers are stored by the short field name (``guardian.email`` → ``email``). */
export function guardianField(target: string) {
  return target.replace(/^guardian\./, '')
}
