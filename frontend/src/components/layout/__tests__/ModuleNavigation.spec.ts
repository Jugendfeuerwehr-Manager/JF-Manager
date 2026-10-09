vi.mock('@/api', () => ({ default: { get: vi.fn().mockResolvedValue({ data: {} }) } }))
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ModuleNavigation from '../ModuleNavigation.vue'
const { auth } = vi.hoisted(() => ({ auth: { isOrgWide: true, hasPerm: vi.fn() } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
const { inbox } = vi.hoisted(() => ({ inbox: { counts: { open_tasks: 0, unread_notices: 0, total: 0, by_category: {} as Record<string, number> } } }))
vi.mock('@/stores/inbox', () => ({ useInboxStore: () => inbox }))
vi.mock('vue-router', () => ({ useRoute: () => ({ path: '/members/42' }) }))
function render() { return mount(ModuleNavigation, { global: { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } } }) }
describe('Module navigation', () => {
  beforeEach(() => { inbox.counts.total = 0; inbox.counts.by_category = {}; auth.isOrgWide = true; auth.hasPerm.mockReset().mockReturnValue(true) })
  it('exposes every module without an overflow menu and highlights detail pages', () => {
    const wrapper = render()
    for (const path of ['/members', '/servicebook', '/training', '/qualifications', '/inventory', '/emails/history', '/users', '/settings']) {
      expect(wrapper.find(`a[href="${path}"]`).exists()).toBe(true)
    }
    expect(wrapper.find('a[href="/orders"]').exists()).toBe(false)
    expect(wrapper.get('a[href="/members"]').attributes('aria-current')).toBe('page')
    expect(wrapper.get('a[href="/"]').attributes('aria-current')).toBeUndefined()
  })
  it('filters modules by current permissions', () => {
    auth.isOrgWide = false
    auth.hasPerm.mockImplementation(permission => permission === 'view_member')
    const wrapper = render()
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/', '/eingang', '/members', '/roles'])
  })
  it('organization visibility alone does not expose subject or administration modules', () => {
    auth.isOrgWide = true
    auth.hasPerm.mockReturnValue(false)
    const wrapper = render()
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/', '/eingang', '/roles'])
  })
  it('exposes configuration for a global category right without organization-wide subject access', () => {
    auth.isOrgWide = false
    auth.hasPerm.mockImplementation(permission => permission === 'settings_manager.view_email_settings')
    const wrapper = render()
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/', '/eingang', '/roles', '/settings'])
  })
  it('finds modules directly by name', async () => {
    const wrapper = render()
    await wrapper.get('input').setValue('ausbildung')
    expect(wrapper.findAll('a').map(link => link.attributes('href'))).toEqual(['/training'])
    await wrapper.get('input').setValue('unbekannt')
    expect(wrapper.text()).toContain('Kein passendes Modul gefunden.')
  })
  it('shows the inbox counter only when something is open', async () => {
    expect(render().find('.nav-badge').exists()).toBe(false)
    inbox.counts.total = 4
    const link = render().get('a[href="/eingang"]')
    expect(link.get('.nav-badge').text()).toBe('4')
    expect(link.get('.nav-badge').attributes('aria-hidden')).toBe('true')
    // The link is announced as "Eingang, 4 offen" (label plus hidden sentence, no repeated name).
    expect(link.get('.sr-only').text()).toBe(', 4 offen')
  })
  it('shows open change requests at Portal with an accessible label', () => {
    expect(render().find('a[href="/portal-verwaltung"] .nav-badge').exists()).toBe(false)
    inbox.counts.by_category = { requests: 2 }
    const link = render().get('a[href="/portal-verwaltung"]')
    expect(link.get('.nav-badge').text()).toBe('2')
    expect(link.get('.nav-badge').attributes('aria-hidden')).toBe('true')
    expect(link.get('.sr-only').text()).toBe(', 2 offene Anträge')
    inbox.counts.by_category = { requests: 1 }
    expect(render().get('a[href="/portal-verwaltung"] .sr-only').text()).toBe(', 1 offener Antrag')
  })
})
