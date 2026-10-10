import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import UserDepartmentRoles from '../organisms/UserDepartmentRoles.vue'
import { useUserRoleAssignmentsStore } from '@/stores/userRoleAssignments'
const { api } = vi.hoisted(() => ({ api: { options: vi.fn(), explain: vi.fn(), preview: vi.fn(), apply: vi.fn() } }))
vi.mock('@/api/role-assignments', () => ({ roleAssignmentsApi: api }))
const choices = {
  people: [{ id: 7, name: 'Demo' }, { id: 8, name: 'Andere Person' }], departments: [{ id: 2, name: 'Nord' }, { id: 3, name: 'Süd' }], organization_allowed: true,
  roles: [{ id: 11, name: 'Dienstbuch', description: 'Dienste verwalten', scope: 'department', department_ids: [2] }, { id: 12, name: 'Inventar', description: '', scope: 'department', department_ids: [3] }],
}
const row = { template_id: 11, role: 'Dienstbuch', department_id: 2, department: 'Nord', permissions: [], sources: [{ source: 'local', source_key: '' }, { source: 'ldap', source_key: 'demo' }] }
const preview = { fingerprint: 'reviewed', person: { id: 7, name: 'Demo' }, role: { id: 11, name: 'Dienstbuch', description: '' }, department: { id: 2, name: 'Nord' }, operation: 'add', changed: true, retained_external: false, permissions: [], added_permissions: ['servicebook.view_service'], removed_permissions: [], effect: 'Rolle hinzufügen' }
const render = () => mount(UserDepartmentRoles, { props: { userId: 7 }, global: { plugins: [createPinia()] } })
describe('roles in user administration', () => {
  beforeEach(() => {
    vi.clearAllMocks(); setActivePinia(createPinia())
    api.options.mockResolvedValue({ data: choices }); api.explain.mockResolvedValue({ data: { roles: [] } })
    api.preview.mockResolvedValue({ data: preview }); api.apply.mockResolvedValue({ data: { saved: true, roles: [row] } })
  })
  it('adds an accordion, filters templates and saves the reviewed assignment for this user', async () => {
    const wrapper = render(); await flushPromises()
    await wrapper.get('#add-role-department').setValue('2')
    await wrapper.findAll('button').find(b => b.text() === 'Abteilung hinzufügen')!.trigger('click')
    const area = wrapper.findAll('details').find(d => d.get('summary').text().includes('Nord'))!
    expect(area.attributes('open')).toBeDefined()
    expect(area.text()).toContain('Dienstbuch'); expect(area.text()).not.toContain('Inventar')
    expect(api.apply).not.toHaveBeenCalled()
    await area.get('select').setValue('11')
    await area.findAll('button').find(b => b.text().includes('Vorlage zuweisen'))!.trigger('click'); await flushPromises()
    expect(api.preview).toHaveBeenCalledWith({ user_id: 7, department_id: 2, template_id: 11, operation: 'add' })
    await wrapper.findAll('button').find(b => b.text() === 'Rollenzuweisung speichern')!.trigger('click'); await flushPromises()
    expect(api.apply).toHaveBeenCalledWith({ user_id: 7, department_id: 2, template_id: 11, operation: 'add', fingerprint: 'reviewed' })
    expect(wrapper.text()).toContain('Rollenzuweisung gespeichert.')
    expect((wrapper.get('#role-template-2').element as HTMLSelectElement).value).toBe('')
    expect(wrapper.text()).toContain('Lokal, LDAP')
  })
  it('reviews local removal while explaining retained external sources', async () => {
    api.explain.mockResolvedValue({ data: { roles: [row] } })
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Externe Zuweisungen')
    await wrapper.findAll('button').find(b => b.text() === 'Lokale Rolle entfernen')!.trigger('click'); await flushPromises()
    expect(api.preview).toHaveBeenCalledWith(expect.objectContaining({ operation: 'remove', user_id: 7, department_id: 2 }))
  })
  it('invalidates a conflict preview and retains the department and template selection', async () => {
    const wrapper = render(); await flushPromises()
    await wrapper.get('#add-role-department').setValue('2')
    await wrapper.findAll('button').find(b => b.text() === 'Abteilung hinzufügen')!.trigger('click')
    await wrapper.get('#role-template-2').setValue('11')
    await wrapper.findAll('button').find(b => b.text().includes('Vorlage zuweisen'))!.trigger('click'); await flushPromises()
    api.apply.mockRejectedValue({ response: { status: 409, data: { detail: 'Bitte erneut prüfen.' } } })
    await wrapper.findAll('button').find(b => b.text() === 'Rollenzuweisung speichern')!.trigger('click'); await flushPromises()
    expect(wrapper.find('.role-preview').exists()).toBe(false)
    expect((wrapper.get('#role-template-2').element as HTMLSelectElement).value).toBe('11')
    expect(wrapper.text()).toContain('Bitte erneut prüfen.')
  })
  it('does not show assignment controls for the own or ineligible account', async () => {
    api.options.mockResolvedValue({ data: { ...choices, people: [] } })
    const wrapper = render(); await flushPromises()
    expect(wrapper.find('#add-role-department').exists()).toBe(false)
    expect(wrapper.text()).toContain('Eigene Rollen')
  })
  it('ignores an old preview after switching users', async () => {
    let resolve!: (value: unknown) => void
    api.preview.mockImplementation(() => new Promise(r => { resolve = r }))
    const store = useUserRoleAssignmentsStore(); await store.load(7)
    const pending = store.review({ department_id: 2, template_id: 11, operation: 'add' })
    await store.load(8); resolve({ data: preview }); await pending
    expect(store.preview).toBeNull(); await store.save(); expect(api.apply).not.toHaveBeenCalled()
  })
})
