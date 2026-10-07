vi.mock('@/api', () => ({ default: { get: vi.fn().mockResolvedValue({ data: {} }) } }))
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ModuleNavigation from '../ModuleNavigation.vue'
const { auth } = vi.hoisted(() => ({ auth: { isOrgWide: true, hasPerm: vi.fn() } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('vue-router', () => ({ useRoute: () => ({ path: '/members/42' }) }))
function render() { return mount(ModuleNavigation, { global: { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } } }) }
describe('Module navigation', () => {
  beforeEach(() => { auth.isOrgWide = true; auth.hasPerm.mockReset().mockReturnValue(true) })
  it('exposes every module without an overflow menu and highlights detail pages', () => {
    const wrapper = render()
    for (const path of ['/members', '/servicebook', '/training', '/qualifications', '/inventory', '/orders', '/emails/history', '/users', '/settings']) {
      expect(wrapper.find(`a[href="${path}"]`).exists()).toBe(true)
    }
    expect(wrapper.get('a[href="/members"]').attributes('aria-current')).toBe('page')
    expect(wrapper.get('a[href="/"]').attributes('aria-current')).toBeUndefined()
  })
  it('filters modules by current permissions', () => {
    auth.isOrgWide = false
    auth.hasPerm.mockImplementation(permission => permission === 'view_member')
    const wrapper = render()
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/', '/members', '/roles'])
  })
  it('organization visibility alone does not expose subject or administration modules', () => {
    auth.isOrgWide = true
    auth.hasPerm.mockReturnValue(false)
    const wrapper = render()
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/', '/roles'])
  })
  it('finds modules directly by name', async () => {
    const wrapper = render()
    await wrapper.get('input').setValue('ausbildung')
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/training'])
    await wrapper.get('input').setValue('unbekannt')
    expect(wrapper.text()).toContain('Kein passendes Modul gefunden.')
  })
})
