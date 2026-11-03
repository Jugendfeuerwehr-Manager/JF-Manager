import { describe, expect, it } from 'vitest'
import type { BuilderReferences, FormSchema } from '@/types/admissions'
import {
  addPage,
  ageOn,
  createElement,
  elementFromPalette,
  paletteItems,
  targetLabel,
  insertElement,
  isVisible,
  issuesByElement,
  locate,
  moveElement,
  removeElement,
  updateElement
} from '../admissionSchema'

function schema(): FormSchema {
  return {
    pages: [
      {
        id: 'p1',
        title: 'Seite',
        sections: [
          { id: 's1', title: 'A', elements: [{ id: 'a', type: 'text', key: 'a' }, { id: 'b', type: 'text', key: 'b' }, { id: 'c', type: 'text', key: 'c' }] },
          { id: 's2', title: 'B', elements: [] }
        ]
      }
    ]
  }
}

const ids = (s: FormSchema, section = 0) => s.pages[0]!.sections[section]!.elements.map((e) => e.id)

describe('admission schema helpers', () => {
  it('creates elements with unique answer keys', () => {
    const base = schema()
    base.pages[0]!.sections[0]!.elements.push({ id: 'x', type: 'text', key: 'text' })
    expect(createElement('text', base).key).toBe('text_2')
    expect(createElement('guardians', base).fields?.map((f) => f.target)).toContain('guardian.name')
    expect(createElement('heading', base).key).toBeUndefined()
  })

  it('inserts without touching the original schema', () => {
    const base = schema()
    const next = insertElement(base, { page: 0, section: 1, index: 0 }, { id: 'n', type: 'divider' })
    expect(ids(next, 1)).toEqual(['n'])
    expect(ids(base, 1)).toEqual([])
  })

  it('moves down within a list and across sections', () => {
    expect(ids(moveElement(schema(), { page: 0, section: 0, index: 0 }, { page: 0, section: 0, index: 2 }))).toEqual(['b', 'a', 'c'])
    expect(ids(moveElement(schema(), { page: 0, section: 0, index: 2 }, { page: 0, section: 0, index: 0 }))).toEqual(['c', 'a', 'b'])
    const across = moveElement(schema(), { page: 0, section: 0, index: 1 }, { page: 0, section: 1, index: 0 })
    expect(ids(across)).toEqual(['a', 'c'])
    expect(ids(across, 1)).toEqual(['b'])
  })

  it('removes, updates and locates elements', () => {
    expect(ids(removeElement(schema(), { page: 0, section: 0, index: 1 }))).toEqual(['a', 'c'])
    expect(locate(updateElement(schema(), 'b', { label: 'Neu' }), 'b')).toEqual({ page: 0, section: 0, index: 1 })
    expect(updateElement(schema(), 'b', { label: 'Neu' }).pages[0]!.sections[0]!.elements[1]!.label).toBe('Neu')
    expect(addPage(schema()).pages).toHaveLength(2)
  })

  it('maps backend issue paths to elements', () => {
    const map = issuesByElement(schema(), [{ path: 'pages.0.sections.0.elements.2', message: 'Fehlt' }])
    expect(map.get('c')).toEqual(['Fehlt'])
  })

  it('computes the age around the birthday', () => {
    expect(ageOn('2012-06-15', new Date('2026-06-14T12:00:00'))).toBe(13)
    expect(ageOn('2012-06-15', new Date('2026-06-15T12:00:00'))).toBe(14)
    expect(ageOn(null)).toBeNull()
  })

  it('evaluates visibility like the backend', () => {
    expect(isVisible({ age_below: 18 }, {}, 17)).toBe(true)
    expect(isVisible({ age_below: 18 }, {}, 18)).toBe(false)
    expect(isVisible({ age_below: 18 }, {}, null)).toBe(true)
    expect(isVisible({ field: 'portal', equals: true }, { portal: true }, null)).toBe(true)
    expect(isVisible({ field: 'portal', equals: true }, {}, null)).toBe(false)
  })
})

const references: BuilderReferences = {
  fields: {
    member: [
      { key: 'member.name', label: 'Vorname', input_type: 'text', sensitive: false },
      { key: 'member.gender', label: 'Geschlecht', input_type: 'select', sensitive: false }
    ],
    guardian: [],
    extra: [
      { key: 'member.extra.groesse', id: 4, label: 'T-Shirt-Größe', input_type: 'select', options: ['152', '164'], help_text: '', department: null }
    ],
    gender_options: []
  },
  legal_kinds: [{ value: 'privacy', label: 'Datenschutz' }],
  consent_kinds: []
}

describe('palette', () => {
  const emptyForm = (): FormSchema => ({ pages: [{ id: 'p', title: 'S', sections: [{ id: 's', title: 'A', elements: [] }] }] })

  it('creates member and additional fields that know their destination', () => {
    const name = elementFromPalette('member:member.name', emptyForm(), references)!
    expect(name).toMatchObject({ type: 'text', target: 'member.name', key: 'vorname', required: true })
    const size = elementFromPalette('extra:member.extra.groesse', emptyForm(), references)!
    expect(size).toMatchObject({ type: 'select', target: 'member.extra.groesse' })
    expect(size.options).toEqual([
      { value: '152', label: '152' },
      { value: '164', label: '164' }
    ])
    expect(targetLabel(size.target, references)).toBe('Zusatzfeld · T-Shirt-Größe')
  })

  it('greys out single-use blocks once they are in the form and refuses to add them again', () => {
    const form = emptyForm()
    form.pages[0]!.sections[0]!.elements.push(
      elementFromPalette('member:member.name', form, references)!,
      elementFromPalette('signature:applicant', form, references)!,
      elementFromPalette('legal:privacy', form, references)!
    )
    const used = new Set(paletteItems(form, references).filter((item) => item.used).map((item) => item.id))
    expect(used).toEqual(new Set(['member:member.name', 'signature:applicant', 'legal:privacy']))
    expect(elementFromPalette('member:member.name', form, references)).toBeNull()
    expect(elementFromPalette('consent', form, references)).not.toBeNull()
  })

  it('makes guardian signatures depend on the age', () => {
    expect(elementFromPalette('signature:guardian_1', emptyForm(), references)!.visible_if).toEqual({ age_below: 18 })
  })
})
