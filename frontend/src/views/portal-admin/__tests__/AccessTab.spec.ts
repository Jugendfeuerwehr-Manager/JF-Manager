import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AccessTab from '../AccessTab.vue'
import { portalAdminApi } from '@/api/portalAdmin'

vi.mock('@/api/portalAdmin', () => ({
  portalAdminApi: { records: vi.fn(), detail: vi.fn(), bulkInvite: vi.fn(), invite: vi.fn(), invitations: vi.fn(), ending: vi.fn() },
}))
const require = vi.fn()
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

const records = [
  { kind: 'parent', id: 1, name: 'Anna Beispiel', email: 'anna@example.org', state: 'none', children: ['Max'] },
  { kind: 'parent', id: 2, name: 'Bernd Muster', email: '', state: 'active', children: [] },
]

function render() {
  return mount(AccessTab, {
    global: {
      stubs: {
        Button: { props: ['label', 'disabled'], template: '<button :disabled="disabled" @click="$emit(\'click\', $event)">{{ label }}</button>' },
        Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /><slot name="footer" /></div>' },
        Paginator: true,
      },
    },
  })
}

describe('AccessTab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(portalAdminApi.records).mockResolvedValue({ data: { count: 2, next: null, previous: null, results: records } } as never)
  })

  it('renders rows with state labels and the missing-email warning', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Anna Beispiel')
    expect(wrapper.text()).toContain('Kein Zugang')
    expect(wrapper.text()).toContain('Aktiv')
    expect(wrapper.text()).toContain('keine E-Mail')
    expect(wrapper.text()).toContain('Einladen')
    expect(wrapper.text()).toContain('Sperren')
  })

  it('enables the bulk button only with a selection and shows the result summary', async () => {
    vi.mocked(portalAdminApi.bulkInvite).mockResolvedValue({ data: { results: [{ parent: 1, result: 'sent' }] } } as never)
    const wrapper = render()
    await flushPromises()
    const bulk = () => wrapper.findAll('button').find(b => b.text().startsWith('Ausgewählte einladen'))!
    expect(bulk().attributes('disabled')).toBeDefined()
    await wrapper.find('input[type=checkbox]').setValue(true)
    expect(bulk().text()).toBe('Ausgewählte einladen (1)')
    expect(bulk().attributes('disabled')).toBeUndefined()
    await bulk().trigger('click')
    await flushPromises()
    expect(portalAdminApi.bulkInvite).toHaveBeenCalledWith([1])
    expect(wrapper.text()).toContain('1 gesendet, 0 übersprungen')
  })

  it('asks for confirmation before suspending', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === 'Sperren')!.trigger('click')
    expect(require).toHaveBeenCalledWith(expect.objectContaining({ header: 'Zugang sperren?', message: expect.stringContaining('Alle Sitzungen werden sofort beendet.') }))
  })
})
