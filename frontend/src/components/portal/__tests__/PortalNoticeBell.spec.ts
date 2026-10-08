import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import PortalNoticeBell from '../PortalNoticeBell.vue'
import { portalApi } from '@/api/portal'

vi.mock('@/api/portal', () => ({ portalApi: { notifications: vi.fn(), markNotificationRead: vi.fn() } }))

const notice = (over = {}) => ({ id: 1, kind: 'assignment', title: 'Zuteilung am Samstag', link: '/portal/termine', updated_at: new Date().toISOString(), read: false, ...over })

async function mountBell(results: unknown[], unread: number) {
  setActivePinia(createPinia())
  vi.mocked(portalApi.notifications).mockResolvedValue({ data: { results, unread } } as never)
  vi.mocked(portalApi.markNotificationRead).mockResolvedValue({ data: {} } as never)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }, { path: '/portal/termine', component: { template: '<div />' } }] })
  await router.push('/'); await router.isReady()
  const wrapper = mount(PortalNoticeBell, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

describe('PortalNoticeBell', () => {
  beforeEach(() => { vi.clearAllMocks(); document.body.innerHTML = '' })

  it('hides the badge at zero and shows the empty state', async () => {
    const { wrapper } = await mountBell([], 0)
    expect(wrapper.find('.badge').exists()).toBe(false)
    expect(wrapper.get('button.bell').attributes('aria-label')).toBe('Hinweise, 0 neu')
    await wrapper.get('button.bell').trigger('click')
    expect(document.body.textContent).toContain('Keine Hinweise')
    wrapper.unmount()
  })

  it('shows the badge, lists notices, marks read and navigates', async () => {
    const { wrapper, router } = await mountBell([notice()], 1)
    expect(wrapper.get('.badge').text()).toBe('1')
    expect(wrapper.get('button.bell').attributes('aria-label')).toBe('Hinweise, 1 neu')
    await wrapper.get('button.bell').trigger('click')
    expect(document.body.textContent).toContain('Zuteilung am Samstag')
    ;(document.body.querySelector('.item') as HTMLElement).click()
    await flushPromises()
    expect(portalApi.markNotificationRead).toHaveBeenCalledWith(1)
    expect(router.currentRoute.value.path).toBe('/portal/termine')
    expect(wrapper.find('.badge').exists()).toBe(false)
    wrapper.unmount()
  })
})
