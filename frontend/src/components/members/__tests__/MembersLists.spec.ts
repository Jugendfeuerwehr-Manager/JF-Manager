import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import MembersMobileList from '../organisms/MembersMobileList.vue'
import MembersTable from '../organisms/MembersTable.vue'
import type { Member } from '@/types/members'

vi.mock('@/composables/usePrivateMedia', () => ({ usePrivateMedia: () => ({ value: undefined }) }))

function member(overrides: Partial<Member> = {}): Member {
  return {
    id: 1, name: 'Lena', lastname: 'Weber', full_name: 'Lena Weber', birthday: '2014-03-14', age: 12,
    email: '', street: '', zip_code: '', city: '', phone: '', mobile: '', notes: '', joined: null,
    identityCardNumber: '', canSwimm: true, gender: '', status: { id: 1, name: 'Aktiv', color: '#16a34a' } as Member['status'],
    group: { id: 2, name: 'Gruppe B' } as Member['group'], storage_location: null, avatar: null, avatar_url: null,
    parents: [
      { id: 7, name: 'Daniel', lastname: 'Weber', full_name: 'Daniel Weber', phone: '', mobile: '' },
      { id: 8, name: 'Katrin', lastname: 'Weber', full_name: 'Katrin Weber', phone: '', mobile: '0171 1234567' },
    ] as Member['parents'],
    has_alert: false, department_ids: [1], ...overrides,
  }
}

const global = { plugins: [PrimeVue], directives: { tooltip: Tooltip } }

describe('MembersMobileList', () => {
  it('opens a member on tap and calls the first reachable parent', async () => {
    const wrapper = mount(MembersMobileList, { props: { members: [member()], loading: false, rows: 20, totalRecords: 1 }, global })
    const call = wrapper.get('a.member-row__call')
    expect(call.attributes('href')).toBe('tel:0171 1234567')
    expect(call.attributes('aria-label')).toBe('Katrin Weber anrufen (Kontakt von Lena Weber)')
    expect(wrapper.text()).toContain('12 J. · Gruppe B')
    expect(wrapper.text()).toContain('Aktiv')
    await wrapper.get('button.member-row__main').trigger('click')
    expect(wrapper.emitted('view')?.[0]).toEqual([member()])
  })

  it('offers no call without a number and keeps destructive actions off the list', () => {
    const wrapper = mount(MembersMobileList, { props: { members: [member({ parents: [] })], loading: false, rows: 20, totalRecords: 1 }, global })
    expect(wrapper.find('a.member-row__call').exists()).toBe(false)
    expect(wrapper.find('[aria-label*="löschen"]').exists()).toBe(false)
  })
})

describe('MembersTable', () => {
  window.matchMedia ??= ((query: string) => ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia

  it('names each row action and shows group and status as text', () => {
    const wrapper = mount(MembersTable, { props: { members: [member({ has_alert: true })], loading: false, first: 0, rows: 20, totalRecords: 1 }, global })
    expect(wrapper.find('[aria-label="Lena Weber bearbeiten"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Lena Weber löschen"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Gruppe B')
    expect(wrapper.text()).toContain('Aktiv')
    expect(wrapper.text()).toContain('Teilnahme prüfen')
  })
})

describe('MembersFilters on phones', () => {
  it('folds the selects behind a filter button that counts active filters', async () => {
    const { default: MembersFilters } = await import('../molecules/MembersFilters.vue')
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 })
    const wrapper = mount(MembersFilters, {
      props: { filters: { search: '', status: 1, group: null, gender: '' }, statuses: [], groups: [] },
      global,
    })
    const toggle = wrapper.get('button[aria-controls="member-filter-fields"]')
    expect(toggle.text()).toContain('Filter (1)')
    expect(wrapper.findAll('.filter-control').length).toBe(1)
    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.findAll('.filter-control').length).toBe(4)
  })
})
