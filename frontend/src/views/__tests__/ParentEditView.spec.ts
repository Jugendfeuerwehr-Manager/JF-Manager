import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ParentEditView from '../ParentEditView.vue'

const { parents, route, push, guards } = vi.hoisted(() => ({
  parents: {
    childOptions: [{ label: 'Mila Muster', value: 4 }],
    childOptionsLoading: false,
    fetchChildOptions: vi.fn(),
    fetchParentById: vi.fn(),
    updateParent: vi.fn(),
    createParent: vi.fn(),
  },
  route: { params: { id: '7' } as Record<string, string> },
  push: vi.fn(),
  guards: [] as Array<() => boolean>,
}))
vi.mock('@/stores/parents', () => ({ useParentsStore: () => parents }))
vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push }),
  onBeforeRouteLeave: (guard: () => boolean) => guards.push(guard),
}))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
vi.mock('@/views/portal-admin/ParentPortalAccessCard.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ hasPerm: () => false }) }))
vi.mock('@/components/members/organisms/AccountLinkCard.vue', () => ({ default: { template: '<div />' } }))

window.matchMedia ??= ((query: string) => ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia
window.HTMLElement.prototype.scrollIntoView ??= function () {}
globalThis.ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver

const parent = {
  id: 7, name: 'Petra', lastname: 'Muster', full_name: 'Petra Muster', email: 'petra@example.invalid', email2: '',
  phone: '', mobile: '', street: '', zip_code: '', city: '', notes: '', children: [4],
}

function render() {
  return mount(ParentEditView, {
    attachTo: document.body,
    global: { plugins: [PrimeVue], stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } },
  })
}

describe('ParentEditView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    guards.length = 0
    route.params = { id: '7' }
    parents.fetchChildOptions.mockResolvedValue([])
    parents.fetchParentById.mockResolvedValue(parent)
    parents.updateParent.mockResolvedValue(parent)
  })

  it('shows field errors at the field, focuses the first one and does not save', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#lastname').setValue('')
    await wrapper.get('#email2').setValue('kein-mail')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(parents.updateParent).not.toHaveBeenCalled()
    expect(wrapper.get('#lastname').attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('#lastname').attributes('aria-describedby')).toBe('lastname-error')
    expect(wrapper.get('#email2-error').text()).toContain('gültige E-Mail-Adresse')
    expect(wrapper.get('.action-bar__status').text()).toContain('2 Felder brauchen deine Aufmerksamkeit')
    expect(document.activeElement?.id).toBe('lastname')
    wrapper.unmount()
  })

  it('places server field errors next to the field and never reports them as saved', async () => {
    parents.updateParent.mockRejectedValue({ response: { status: 400, data: { email: ['Diese Adresse ist bereits vergeben.'] } } })
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#phone').setValue('0123 4567')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('#email-error').text()).toContain('Diese Adresse ist bereits vergeben.')
    expect(push).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Ungespeicherte Änderungen')
    wrapper.unmount()
  })

  it('asks before leaving with unsaved changes and lets a successful save through', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = render()
    await flushPromises()
    const leave = guards[0]!
    expect(leave()).toBe(true)
    expect(confirm).not.toHaveBeenCalled()

    await wrapper.get('#city').setValue('Musterstadt')
    expect(leave()).toBe(false)
    expect(confirm).toHaveBeenCalledOnce()

    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(parents.updateParent).toHaveBeenCalledWith(7, expect.objectContaining({ city: 'Musterstadt', children: [4] }))
    expect(push).toHaveBeenCalledWith('/parents')
    expect(leave()).toBe(true)
    confirm.mockRestore()
    wrapper.unmount()
  })

  it('shows a load error with retry instead of redirecting', async () => {
    parents.fetchParentById.mockRejectedValueOnce({ response: { status: 500 } })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Elternteil konnte nicht geladen werden')
    expect(push).not.toHaveBeenCalled()
    await wrapper.findAll('button').find((button) => button.text() === 'Erneut versuchen')!.trigger('click')
    await flushPromises()
    expect((wrapper.get('#name').element as HTMLInputElement).value).toBe('Petra')
    wrapper.unmount()
  })
})
