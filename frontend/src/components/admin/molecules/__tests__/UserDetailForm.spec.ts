import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UserDetailForm from '../UserDetailForm.vue'
import type { AdminUserDetail } from '@/types/admin'

const { createUser, updateUser, fetchUsers } = vi.hoisted(() => ({
  createUser: vi.fn(), updateUser: vi.fn(), fetchUsers: vi.fn(),
}))
vi.mock('@/stores/admin', () => ({ useAdminStore: () => ({
  groups: [], groupsLoading: false, createUser, updateUser, fetchUsers,
}) }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({
  hasPerm: () => true, user: { id: 1, is_superuser: true },
}) }))
vi.mock('@/components/emails/organisms/TiptapEditor.vue', () => ({ default: { template: '<div />' } }))

function render(user?: AdminUserDetail) {
  return mount(UserDetailForm, { props: { user }, global: { stubs: {
    InputText: { props: ['modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
    Fieldset: { template: '<div><slot /></div>' },
    Checkbox: true, MultiSelect: true, Password: true, Button: true,
    Message: true, PermissionInfoIcon: true,
  } } })
}

describe('UserDetailForm theme preferences', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    createUser.mockResolvedValue({ id: 2 })
    updateUser.mockResolvedValue({ id: 2 })
    fetchUsers.mockResolvedValue([])
  })

  it('creates a user without sending an invalid empty theme, leaving the backend default effective', async () => {
    const wrapper = render()
    await wrapper.get('#username').setValue('synthetic-new-user')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(createUser).toHaveBeenCalledOnce()
    expect(createUser.mock.calls[0]![0]).toMatchObject({ username: 'synthetic-new-user' })
    expect(createUser.mock.calls[0]![0]).not.toHaveProperty('theme_mode')
    expect(wrapper.emitted('saved')).toEqual([[2]])
  })

  it.each(['dark', undefined])('does not overwrite personal theme preferences when editing (%s)', async (theme) => {
    const user = { id: 2, username: 'synthetic-existing-user', first_name: '', last_name: '',
      email: '', is_active: true, is_staff: false, is_superuser: false, groups: [], theme_mode: theme,
    } as unknown as AdminUserDetail
    const wrapper = render(user)
    await wrapper.get('#first_name').setValue('Example')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(updateUser).toHaveBeenCalledWith(2, expect.objectContaining({ first_name: 'Example' }))
    expect(updateUser.mock.calls[0]![1]).not.toHaveProperty('theme_mode')
    expect(updateUser.mock.calls[0]![1]).not.toHaveProperty('group_ids')
    expect(wrapper.emitted('saved')).toEqual([[2]])
  })
})
