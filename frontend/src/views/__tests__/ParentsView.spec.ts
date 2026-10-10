import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ParentsView from '../ParentsView.vue'

const { parents, departments, route, replace, push, require } = vi.hoisted(() => ({
  parents: {
    parents: [] as unknown[],
    loading: false,
    pagination: { count: 0, next: null, previous: null },
    emailAllParentsLink: '',
    fetchParents: vi.fn(),
    deleteParent: vi.fn(),
  },
  departments: { activeDepartment: null },
  route: { query: {} as Record<string, string> },
  replace: vi.fn(),
  push: vi.fn(),
  require: vi.fn(),
}))
vi.mock('@/stores/parents', () => ({ useParentsStore: () => parents }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => departments }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push, replace }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

window.matchMedia ??= ((query: string) => ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia

const fictional = [
  { id: 1, name: 'Petra', lastname: 'Muster', full_name: 'Petra Muster', email: 'petra@example.invalid', email2: '', phone: '0123 45 67', mobile: '', street: '', zip_code: '', city: '', notes: '', children: [4] },
  { id: 2, name: 'Uwe', lastname: 'Beispiel', full_name: 'Uwe Beispiel', email: '', email2: '', phone: '', mobile: '', street: '', zip_code: '', city: '', notes: '', children: [] },
]

function render() {
  return mount(ParentsView, {
    global: {
      plugins: [PrimeVue],
      directives: { tooltip: () => {} },
      stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } },
    },
  })
}

describe('ParentsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.innerWidth = 1440
    route.query = {}
    parents.parents = []
    parents.pagination = { count: 0, next: null, previous: null }
    parents.fetchParents.mockImplementation(async () => {
      parents.parents = fictional
      parents.pagination = { count: 2, next: null, previous: null }
    })
  })

  it('shows a missing permission instead of an empty list and offers no retry', async () => {
    parents.fetchParents.mockRejectedValue({ response: { status: 403 } })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Berechtigung für Eltern')
    expect(wrapper.text()).not.toContain('Keine Eltern gefunden')
    expect(wrapper.text()).not.toContain('Erneut versuchen')
  })

  it('offers a retry after a failed load', async () => {
    parents.fetchParents.mockRejectedValueOnce({ response: { status: 500 } })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Eltern konnten nicht geladen werden')
    await wrapper.findAll('button').find((button) => button.text() === 'Erneut versuchen')!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Petra Muster')
  })

  it('has one main action, named row actions and a text status for unlinked contacts', async () => {
    const wrapper = render()
    await flushPromises()
    const header = wrapper.get('.overview-header__actions')
    expect(header.findAll('button').map((button) => button.text())).toEqual(['E-Mail an diese Seite', 'Elternteil anlegen'])
    expect(wrapper.find('[aria-label="Petra Muster bearbeiten"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Uwe Beispiel löschen"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('1 Mitglied')
    expect(wrapper.text()).toContain('Ohne Mitglied')
    expect(wrapper.get('a[href="tel:01234567"]').text()).toBe('0123 45 67')
  })

  it('reads search, page and sorting from the URL and asks before deleting', async () => {
    route.query = { search: 'Muster', page: '2', rows: '10', sortField: 'name', sortOrder: '-1' }
    const wrapper = render()
    await flushPromises()
    expect(parents.fetchParents).toHaveBeenCalledWith({ offset: 10, limit: 10, search: 'Muster', ordering: '-name' })
    await wrapper.get('[aria-label="Uwe Beispiel löschen"]').trigger('click')
    expect(require).toHaveBeenCalledWith(expect.objectContaining({ header: 'Elternteil löschen', acceptClass: 'p-button-danger' }))
    expect(parents.deleteParent).not.toHaveBeenCalled()
  })
})
