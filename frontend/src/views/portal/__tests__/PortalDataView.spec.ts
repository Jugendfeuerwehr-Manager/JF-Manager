import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PortalDataView from '../PortalDataView.vue'
import { portalApi } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'
import { changeRequestsApi } from '@/api/changeRequests'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn(), person: vi.fn() } }))
vi.mock('@/api/changeRequests', () => ({ changeRequestsApi: { list: vi.fn(), submit: vi.fn(), withdraw: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/portal' } } } }))

const contact = { first_name: 'Mia', last_name: 'Becker', street: 'Lindenweg 4', zip_code: '12345', city: 'Musterstadt', phone: '', mobile: '0151 1', email: '' }
const account = { first_name: 'Anna', last_name: 'Becker', email: 'a@example.org' }

const openRequest = {
  id: 7, kind: 'member', target_id: 2, person_name: 'Mia Becker', status: 'open', status_label: 'In Prüfung', version: 1,
  fields: [{ field: 'mobile', label: 'Mobil', old: '0151 1', new: '0170 9' }],
  decision_note: '', created_at: '2026-10-06T16:22:00Z', updated_at: '2026-10-06T16:22:00Z', decided_at: null,
}

async function render(person: unknown, parent: unknown = null, requests: unknown[] = []) {
  vi.mocked(changeRequestsApi.list).mockResolvedValue({ data: { results: requests } } as never)
  vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [{ id: 2, relation: 'child', first_name: 'Mia', last_name: 'Becker' }], parent } } as never)
  if (person instanceof Error) vi.mocked(portalApi.person).mockRejectedValue(person)
  else vi.mocked(portalApi.person).mockResolvedValue({ data: person } as never)
  await usePortalStore().fetchMe()
  const wrapper = mount(PortalDataView, { global: { stubs: { Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button type="button" :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' } } }, attachTo: document.body })
  await flushPromises()
  return wrapper
}

describe('PortalDataView', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('renders only the released categories', async () => {
    const w = await render({
      id: 2, relation: 'child', categories: ['contact', 'birthday', 'group', 'qualifications'], contact, birthday: '2014-03-14', age: 12,
      group: { group: 'Gruppe 2', departments: ['Abteilung Mitte'] },
      qualifications: [
        { type: 'Jugendflamme 1', acquired: '2025-05-10', expires: null, valid: true },
        { type: 'Erste Hilfe', acquired: null, expires: '2024-03-01', valid: false },
      ],
    })
    expect(portalApi.person).toHaveBeenCalledWith(2)
    const text = w.text()
    expect(text).toContain('Name und Kontakt')
    expect(text).toContain('14.03.2014')
    expect(text).toContain('Gruppe 2 · Abteilung Mitte')
    expect(text).toContain('seit 05/2025')
    expect(text).toContain('gültig bis 03/2024')
    expect(text).toContain('abgelaufen')
    expect(text).toContain('Nur lesbar. Nachweise pflegt die Jugendleitung.')
    expect(text).toContain('Änderung beantragen')
    expect(text).toContain('erst nach Freigabe')
    for (const absent of ['Ausrüstung', 'Sonderaufgaben', 'Mitgliedschaft', 'Ausweis', 'Schwimmfähigkeit', 'Weitere Kontaktpersonen', 'Meine Kontaktdaten']) {
      expect(text).not.toContain(absent)
    }
  })

  it('shows the parent contact card when the account has parent data', async () => {
    const parent = { first_name: 'Anna', last_name: 'Becker', street: 'Weg 1', zip_code: '1', city: 'X', phone: '', mobile: '0170', email: 'a@example.org', email2: '' }
    const w = await render({ id: 2, relation: 'child', categories: ['contact'], contact }, parent)
    expect(w.text()).toContain('Meine Kontaktdaten')
    expect(w.text()).toContain('0170')
    expect(w.text()).not.toContain('Nur lesbar. Änderungen meldest du')
  })

  it('shows the pending request as a banner and blocks a second one', async () => {
    const w = await render({ id: 2, relation: 'child', categories: ['contact'], contact }, null, [openRequest])
    expect(w.text()).toContain('Änderung in Prüfung')
    expect(w.text()).toContain('Änderung beantragen (Antrag offen)')
    expect(w.findAll('button').find(b => b.text() === 'Änderung beantragen (Antrag offen)')!.attributes('disabled')).toBeDefined()
    w.unmount()
  })

  it('withdraws the open request and drops the banner', async () => {
    vi.mocked(changeRequestsApi.withdraw).mockResolvedValue({ data: { ...openRequest, status: 'withdrawn' } } as never)
    const w = await render({ id: 2, relation: 'child', categories: ['contact'], contact }, null, [openRequest])
    await w.findAll('button').find(b => b.text() === 'Zurückziehen')!.trigger('click')
    await flushPromises()
    expect(changeRequestsApi.withdraw).toHaveBeenCalledWith(7)
    expect(w.text()).not.toContain('Änderung in Prüfung')
    w.unmount()
  })

  it('sends only the changed field with the member target and shows server field errors', async () => {
    vi.mocked(changeRequestsApi.submit).mockRejectedValueOnce(Object.assign(new Error('bad'), { response: { status: 400, data: { code: 'invalid', detail: 'x', fields: { mobile: 'Nur Ziffern erlaubt.' } } } }))
    const w = await render({ id: 2, relation: 'child', categories: ['contact'], contact })
    await w.findAll('button').find(b => b.text() === 'Änderung beantragen')!.trigger('click')
    await w.get('#cr-mobile').setValue('abc')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(changeRequestsApi.submit).toHaveBeenCalledWith({ kind: 'member', id: 2 }, { mobile: 'abc' })
    expect(w.get('#cr-mobile-error').text()).toContain('Nur Ziffern erlaubt.')
    vi.mocked(changeRequestsApi.submit).mockResolvedValueOnce({ data: openRequest } as never)
    await w.get('#cr-mobile').setValue('0170 9')
    await w.get('form').trigger('submit')
    await flushPromises()
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    expect(w.text()).toContain('Änderung in Prüfung')
    w.unmount()
  })

  it('reports the decided result including the note', async () => {
    const decided = { ...openRequest, status: 'partial', status_label: 'Teilweise übernommen', decision_note: 'Mobil stimmt, Adresse bitte per Mail.', decided_at: '2026-10-07T08:00:00Z', fields: [{ ...openRequest.fields[0], decision: 'apply' }] }
    const w = await render({ id: 2, relation: 'child', categories: ['contact'], contact }, null, [decided])
    expect(w.text()).toContain('Änderung teilweise übernommen')
    expect(w.text()).toContain('Mobil stimmt, Adresse bitte per Mail.')
    w.unmount()
  })

  it('shows a calm message for a foreign id (404)', async () => {
    const w = await render(Object.assign(new Error('nf'), { response: { status: 404, data: {} } }))
    expect(w.text()).toContain('Für diese Person sind keine Daten verfügbar.')
    expect(w.text()).not.toContain('Name und Kontakt')
  })

  it('shows the server error with a retry', async () => {
    const w = await render(Object.assign(new Error('boom'), { response: { status: 500, data: { detail: 'Server kaputt' } } }))
    expect(w.text()).toContain('Server kaputt')
    expect(w.text()).toContain('Erneut versuchen')
  })
})
