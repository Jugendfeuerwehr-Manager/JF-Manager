import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import PortalChangeRequestSheet from '../PortalChangeRequestSheet.vue'
import PortalChangeRequestBanner from '../PortalChangeRequestBanner.vue'
import { MEMBER_FIELDS, PARENT_FIELDS } from '@/utils/changeRequestFields'
import type { ChangeRequest } from '@/types/changeRequests'

const current = { name: 'Mia', lastname: 'Becker', street: 'Lindenweg 4', zip_code: '12345', city: 'Musterstadt', phone: '', mobile: '0151 2345678', email: '' }
let wrapper: VueWrapper | null = null
const render = (props: Record<string, unknown> = {}) => {
  wrapper = mount(PortalChangeRequestSheet, { props: { title: 'Mia', fields: MEMBER_FIELDS, current, ...props }, global: { plugins: [PrimeVue] }, attachTo: document.body })
  return wrapper
}
afterEach(() => { wrapper?.unmount(); wrapper = null })
const button = (w: VueWrapper, text: string) => w.findAll('button').find(b => b.text() === text)!

const open: ChangeRequest = {
  id: 7, kind: 'member', target_id: 2, person_name: 'Mia Becker', status: 'open', status_label: 'In Prüfung', version: 1,
  fields: [{ field: 'mobile', label: 'Mobil', old: '0151 2345678', new: '0170 9876543' }],
  decision_note: '', created_at: '2026-10-06T16:22:00Z', updated_at: '2026-10-06T16:22:00Z', decided_at: null,
}

describe('PortalChangeRequestSheet', () => {
  it('prefills the inputs and disables sending until something changed', () => {
    const w = render()
    expect((w.get('#cr-mobile').element as HTMLInputElement).value).toBe('0151 2345678')
    expect(button(w, 'Änderung beantragen').attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('erst nach Freigabe')
  })

  it('sends only the changed fields, trimmed', async () => {
    const w = render()
    await w.get('#cr-mobile').setValue('  0170 9876543 ')
    await w.get('#cr-city').setValue('Neustadt')
    await w.get('form').trigger('submit')
    expect(w.emitted('submit')![0]).toEqual([{ mobile: '0170 9876543', city: 'Neustadt' }])
  })

  it('does not send a field that was changed back', async () => {
    const w = render()
    await w.get('#cr-mobile').setValue('0170')
    await w.get('#cr-mobile').setValue('0151 2345678')
    await w.get('form').trigger('submit')
    expect(w.emitted('submit')).toBeUndefined()
  })

  it('shows server errors at the field and as a summary', () => {
    const w = render({ fieldErrors: { mobile: 'Nur Ziffern erlaubt.' }, error: 'Bitte prüfe die markierten Felder.' })
    expect(w.get('#cr-mobile').attributes('aria-invalid')).toBe('true')
    expect(w.get('#cr-mobile').attributes('aria-describedby')).toBe('cr-mobile-error')
    expect(w.get('#cr-mobile-error').text()).toContain('Nur Ziffern erlaubt.')
    expect(w.text()).toContain('Bitte prüfe die markierten Felder.')
  })

  it('edits an open request: new values prefill, compared with the stored data', async () => {
    const w = render({ existing: open })
    expect((w.get('#cr-mobile').element as HTMLInputElement).value).toBe('0170 9876543')
    expect(w.text()).toContain('Du bearbeitest deinen offenen Antrag.')
    await w.get('form').trigger('submit')
    expect(w.emitted('submit')![0]).toEqual([{ mobile: '0170 9876543' }])
  })

  it('offers E-Mail 1 and E-Mail 2 for the parent record only', () => {
    expect(PARENT_FIELDS.map(f => f.label)).toEqual(expect.arrayContaining(['E-Mail 1', 'E-Mail 2']))
    expect(MEMBER_FIELDS.map(f => f.field)).not.toContain('email2')
  })
})

describe('PortalChangeRequestBanner', () => {
  it('shows old to new and that nothing changed yet; emits edit and withdraw', async () => {
    const w = mount(PortalChangeRequestBanner, { props: { request: open }, global: { plugins: [PrimeVue] } })
    expect(w.text()).toContain('Änderung in Prüfung')
    expect(w.text()).toContain('0151 2345678')
    expect(w.text()).toContain('0170 9876543')
    expect(w.text()).toContain('Bis dahin gelten die bisherigen Daten')
    await button(w, 'Antrag bearbeiten').trigger('click')
    await button(w, 'Zurückziehen').trigger('click')
    expect(w.emitted('edit')).toHaveLength(1)
    expect(w.emitted('withdraw')).toHaveLength(1)
  })
})
