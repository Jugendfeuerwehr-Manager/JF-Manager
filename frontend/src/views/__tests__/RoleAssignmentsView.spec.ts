import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RoleAssignmentsView from '../RoleAssignmentsView.vue'

const { options, explain, preview, apply } = vi.hoisted(() => ({ options: vi.fn(), explain: vi.fn(), preview: vi.fn(), apply: vi.fn() }))
vi.mock('@/api/role-assignments', () => ({ roleAssignmentsApi: { options, explain, preview, apply } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { id: 1 } }) }))
vi.mock('vue-router', () => ({ onBeforeRouteLeave: vi.fn() }))
const choices = { people: [{ id: 2, name: 'Testperson' }], departments: [{ id: 10, name: 'Nord' }], organization_allowed: false,
  roles: [{ id: 3, name: 'Betreuer', description: 'Anwesenheit erfassen', scope: 'department', department_ids: [10] }] }
const result = { fingerprint: 'reviewed', person: { id: 2, name: 'Testperson' }, role: { id: 3, name: 'Betreuer' }, department: { id: 10, name: 'Nord' },
  operation: 'add', changed: true, retained_external: false, permissions: ['servicebook.change_attendance'], added_permissions: ['servicebook.change_attendance'], removed_permissions: [], effect: 'Lokale Zuweisung hinzufügen.' }
function render() {
  return mount(RoleAssignmentsView, { global: { stubs: {
    Button: { props: ['label', 'disabled', 'type'], template: '<button :type="type || \'button\'" :disabled="disabled">{{ label }}</button>' },
    Message: { template: '<div><slot /></div>' },
  } } })
}
const button = (wrapper: ReturnType<typeof render>, label: string) => wrapper.findAll('button').find(row => row.text() === label)!
async function choose(wrapper: ReturnType<typeof render>) {
  await flushPromises()
  await wrapper.get('#role-person').setValue('2')
  await flushPromises()
  await wrapper.get('#role-area').setValue('10')
  await wrapper.get('#role-choice').setValue('3')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}
describe('RoleAssignmentsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    options.mockResolvedValue({ data: choices })
    explain.mockResolvedValue({ data: { roles: [] } })
    preview.mockResolvedValue({ data: result })
    apply.mockResolvedValue({ data: { saved: true, roles: [] } })
  })
  it('reviews the selected person, scope and role and saves only after confirmation', async () => {
    const wrapper = render()
    await choose(wrapper)
    expect(preview).toHaveBeenCalledWith({ user_id: 2, department_id: 10, template_id: 3, operation: 'add' })
    expect(apply).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Anwesenheiten bearbeiten')
    expect(wrapper.get('code').text()).toBe('servicebook.change_attendance')
    await button(wrapper, 'Zuweisung speichern').trigger('click')
    await flushPromises()
    expect(apply).toHaveBeenCalledWith({ user_id: 2, department_id: 10, template_id: 3, operation: 'add', fingerprint: 'reviewed' })
    expect(wrapper.text()).toContain('Zuweisung gespeichert.')
  })
  it('retains selections after a conflict and requires a new preview', async () => {
    apply.mockRejectedValue({ response: { status: 409, data: { detail: 'Wirkung erneut prüfen.' } } })
    const wrapper = render()
    await choose(wrapper)
    await button(wrapper, 'Zuweisung speichern').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Wirkung erneut prüfen.')
    expect((wrapper.get('#role-choice').element as HTMLSelectElement).value).toBe('3')
    expect(wrapper.find('[aria-label="Wirkung der Zuweisung"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Zuweisung gespeichert.')
  })
  it('shows own explanation when assigning is forbidden', async () => {
    options.mockRejectedValue({ response: { status: 403 } })
    explain.mockResolvedValue({ data: { roles: [{ role: 'Betreuer', template_id: 3, department_id: 10, department: 'Nord', sources: [{ source: 'oidc', source_key: '7' }], permissions: ['servicebook.view_service'] }] } })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('OIDC (extern verwaltet)')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.findAll('button').some(row => row.text() === 'Wirkung prüfen')).toBe(false)
  })
  it('reviews local removal while explaining preserved external rights', async () => {
    explain.mockResolvedValue({ data: { roles: [{ role: 'Betreuer', template_id: 3, department_id: 10, department: 'Nord', sources: [{ source: 'local', source_key: '' }, { source: 'ldap', source_key: '9' }], permissions: [] }] } })
    preview.mockResolvedValue({ data: { ...result, operation: 'remove', retained_external: true } })
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#role-person').setValue('2')
    await flushPromises()
    await button(wrapper, 'Lokale Zuweisung entfernen …').trigger('click')
    await flushPromises()
    expect(preview).toHaveBeenCalledWith({ user_id: 2, department_id: 10, template_id: 3, operation: 'remove' })
    expect(wrapper.text()).toContain('Eine externe Quelle erhält diese Rolle')
  })
  it('discards a delayed preview when the selection changes', async () => {
    let resolve!: (value: { data: typeof result }) => void
    preview.mockImplementation(() => new Promise(done => { resolve = done }))
    const wrapper = render()
    await choose(wrapper)
    await wrapper.get('#role-area').setValue('')
    resolve({ data: result })
    await flushPromises()
    expect(wrapper.find('[aria-label="Wirkung der Zuweisung"]').exists()).toBe(false)
  })
  it('does not save if the explicit confirmation is cancelled', async () => {
    vi.mocked(window.confirm).mockReturnValue(false)
    const wrapper = render()
    await choose(wrapper)
    await button(wrapper, 'Zuweisung speichern').trigger('click')
    expect(apply).not.toHaveBeenCalled()
  })
})
