import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DeleteServiceButton from '../molecules/DeleteServiceButton.vue'
const { auth, requireConfirm, deleteService, push, add } = vi.hoisted(() => ({
  auth: { user: { is_superuser: false, permissions: [] as string[], department_roles: [] as { department_id: number; permissions: string[] }[] } },
  requireConfirm: vi.fn(), deleteService: vi.fn(), push: vi.fn(), add: vi.fn(),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/servicebook', () => ({ useServicebookStore: () => ({ deleteService }) }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: requireConfirm }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add }) }))
const render = () => mount(DeleteServiceButton, { props: { service: { id: 4, department: 7, topic: 'Testdienst' } } })
describe('service deletion', () => {
  beforeEach(() => { vi.clearAllMocks(); auth.user.is_superuser = true; auth.user.permissions = []; auth.user.department_roles = []; deleteService.mockResolvedValue(undefined) })
  it('waits for confirmation then deletes and returns to the servicebook', async () => {
    const wrapper = render(); await wrapper.get('button').trigger('click')
    expect(deleteService).not.toHaveBeenCalled()
    expect(requireConfirm.mock.calls[0]![0].message).toContain('Anwesenheiten')
    await requireConfirm.mock.calls[0]![0].accept(); await flushPromises()
    expect(deleteService).toHaveBeenCalledWith(4)
    expect(push).toHaveBeenCalledWith({ name: 'servicebook' })
  })
  it('restricts the button to global or matching department delete rights', () => {
    auth.user.is_superuser = false
    auth.user.department_roles = [{ department_id: 8, permissions: ['servicebook.delete_service'] }]
    expect(render().find('button').exists()).toBe(false)
    auth.user.department_roles[0]!.department_id = 7
    expect(render().find('button').exists()).toBe(true)
  })
  it('shows errors without navigating away', async () => {
    deleteService.mockRejectedValue(new Error('offline'))
    await render().get('button').trigger('click'); await requireConfirm.mock.calls[0]![0].accept()
    expect(push).not.toHaveBeenCalled()
    expect(add).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
  })
})
