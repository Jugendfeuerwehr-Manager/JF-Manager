import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import UsersPanel from '../organisms/UsersPanel.vue'

const { admin, toastAdd, confirmRequire } = vi.hoisted(() => ({
  admin: {
    users: [] as unknown[], usersLoading: false,
    fetchUsers: vi.fn(), fetchGroups: vi.fn(), fetchUser: vi.fn(), resetUserMfa: vi.fn(),
  },
  toastAdd: vi.fn(),
  confirmRequire: vi.fn(),
}))
vi.mock('@/components/admin/organisms/UserDepartmentRoles.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/stores/admin', () => ({ useAdminStore: () => admin }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { is_superuser: true }, hasPerm: () => true }) }))
vi.mock('@/stores/users', () => ({ useUsersStore: () => ({ currentUser: { id: 1 }, fetchCurrentUser: vi.fn() }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: confirmRequire }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const base = { id: 7, username: 'betreuer', full_name: 'Betreuer', first_name: '', last_name: '', is_superuser: false, is_staff: false, is_active: true, permissions: [] }

function render() {
  return mount(UsersPanel, { global: { plugins: [PrimeVue], stubs: { UserDetailForm: true } } })
}

describe('UsersPanel – second factor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    admin.users = [{ ...base, mfa_enabled: true }]
    confirmRequire.mockImplementation((options: { accept: () => Promise<void> }) => options.accept())
  })

  it('resets the second factor of an ordinary account after confirmation', async () => {
    admin.fetchUser.mockResolvedValue({ ...base, mfa: { enabled: true, totp: true, passkeys: 1, ui_reset_allowed: true, reset_blocker: null } })
    admin.resetUserMfa.mockResolvedValue({ enabled: false })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('2FA')
    await wrapper.get('.user-list-item').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Aktiv: Authenticator-App, 1 Passkey.')
    await wrapper.findAll('button').find(b => b.text().includes('Zwei-Faktor-Anmeldung zurücksetzen'))!.trigger('click')
    await flushPromises()
    expect(confirmRequire).toHaveBeenCalled()
    expect(admin.resetUserMfa).toHaveBeenCalledWith(7)
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success' }))
    wrapper.unmount()
  })

  it('points to the console for administrative accounts', async () => {
    admin.fetchUser.mockResolvedValue({ ...base, is_staff: true, mfa: { enabled: true, totp: true, passkeys: 0, ui_reset_allowed: false, reset_blocker: 'console_only' } })
    const wrapper = render()
    await flushPromises()
    await wrapper.get('.user-list-item').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('jfctl admin reset-mfa --user betreuer')
    expect(wrapper.findAll('button').some(b => b.text().includes('Zwei-Faktor-Anmeldung zurücksetzen'))).toBe(false)
    wrapper.unmount()
  })
})
