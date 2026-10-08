import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PortalDataView from '../PortalDataView.vue'
import { portalApi } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn(), person: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/portal' } } } }))

const contact = { first_name: 'Mia', last_name: 'Becker', street: 'Lindenweg 4', zip_code: '12345', city: 'Musterstadt', phone: '', mobile: '0151 1', email: '' }
const account = { first_name: 'Anna', last_name: 'Becker', email: 'a@example.org' }

async function render(person: unknown, parent: unknown = null) {
  vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [{ id: 2, relation: 'child', first_name: 'Mia', last_name: 'Becker' }], parent } } as never)
  if (person instanceof Error) vi.mocked(portalApi.person).mockRejectedValue(person)
  else vi.mocked(portalApi.person).mockResolvedValue({ data: person } as never)
  await usePortalStore().fetchMe()
  const wrapper = mount(PortalDataView, { global: { stubs: { Button: { props: ['label', 'disabled'], template: '<button :disabled="disabled">{{ label }}</button>' } } } })
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
    expect(text).toContain('Änderung beantragen (bald verfügbar)')
    for (const absent of ['Ausrüstung', 'Sonderaufgaben', 'Mitgliedschaft', 'Ausweis', 'Schwimmfähigkeit', 'Weitere Kontaktpersonen', 'Meine Kontaktdaten']) {
      expect(text).not.toContain(absent)
    }
  })

  it('shows the parent contact card when the account has parent data', async () => {
    const parent = { first_name: 'Anna', last_name: 'Becker', street: 'Weg 1', zip_code: '1', city: 'X', phone: '', mobile: '0170', email: 'a@example.org', email2: '' }
    const w = await render({ id: 2, relation: 'child', categories: ['contact'], contact }, parent)
    expect(w.text()).toContain('Meine Kontaktdaten')
    expect(w.text()).toContain('0170')
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
