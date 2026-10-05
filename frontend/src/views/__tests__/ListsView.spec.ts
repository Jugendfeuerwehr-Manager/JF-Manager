import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ListsView from '../ListsView.vue'

const { listsStore, membersStore, authStore, departmentsStore, addToast, push } = vi.hoisted(() => ({
  listsStore: { lists: [] as Array<Record<string, unknown>>, loading: false, saving: false, currentList: null as null | Record<string, unknown>, fetchLists: vi.fn(), createList: vi.fn(), updateList: vi.fn(), fetchList: vi.fn(), deleteList: vi.fn() },
  membersStore: { fetchMembers: vi.fn() },
  authStore: { user: { is_superuser: true, permissions: [], department_roles: [] as Array<{ department_id: number; permissions: string[] }> } },
  departmentsStore: { departments: [{ id: 7, name: 'Jugend', is_active: true }, { id: 8, name: 'Musik', is_active: false }], error: null as string | null, fetchDepartments: vi.fn() },
  addToast: vi.fn(),
  push: vi.fn(),
}))

vi.mock('@/stores/lists', () => ({ useMemberListsStore: () => listsStore }))
vi.mock('@/stores/members', () => ({ useMembersStore: () => membersStore }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authStore }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => departmentsStore }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: vi.fn() }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: addToast }) }))

const existingList = {
  id: 21, name: 'Dienstabend', description: 'Bestehende Beschreibung', color: '#2563EB', department: 7,
  member_count: 0, checked_count: 0, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}

function render() {
  return mount(ListsView, {
    global: {
      stubs: {
        Button: { props: ['label', 'icon', 'disabled', 'title'], template: '<button :disabled="disabled" :title="title" :aria-label="label || icon" @click="$emit(\'click\', $event)">{{ label }}<slot /></button>' },
        Card: { template: '<article><slot name="header"/><slot name="content"/></article>' },
        ConfirmDialog: true,
        Dialog: { props: ['visible', 'header'], template: '<div class="dialog" :data-visible="visible"><h2>{{ header }}</h2><slot/><slot name="footer"/></div>' },
        InputText: { props: ['modelValue', 'id', 'disabled'], template: '<input :id="id" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
        Message: { template: '<div role="alert"><slot /></div>' },
        ProgressSpinner: true,
        Select: {
          props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'placeholder', 'disabled', 'id'],
          template: '<select :id="id" :value="modelValue ?? \'\'" :disabled="disabled" @change="$emit(\'update:modelValue\', $event.target.value ? Number($event.target.value) : null)"><option value="">{{ placeholder }}</option><option v-for="option in options" :key="option[optionValue]" :value="option[optionValue]">{{ option[optionLabel] }}</option></select>',
        },
        Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
        Textarea: { props: ['modelValue', 'id', 'disabled'], template: '<textarea :id="id" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
        Toast: true,
      },
    },
  })
}

describe('ListsView department-aware forms', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listsStore.lists = []
    listsStore.loading = false
    listsStore.saving = false
    listsStore.currentList = null
    authStore.user = { is_superuser: true, permissions: [], department_roles: [] }
    departmentsStore.departments = [{ id: 7, name: 'Jugend', is_active: true }, { id: 8, name: 'Musik', is_active: false }]
    departmentsStore.error = null
    departmentsStore.fetchDepartments.mockResolvedValue(undefined)
    listsStore.fetchLists.mockResolvedValue([])
    membersStore.fetchMembers.mockResolvedValue([])
    listsStore.createList.mockResolvedValue({ ...existingList, id: 22, name: 'Neue Liste' })
    listsStore.updateList.mockResolvedValue(existingList)
  })

  it('sends the explicitly selected allowed department and retains form state on an API error', async () => {
    listsStore.createList.mockRejectedValueOnce({ response: { data: { department: 'Keine Schreibberechtigung für diese Abteilung.' } } })
    const wrapper = render()
    await flushPromises()
    const setup = (wrapper.vm as unknown as { $: { setupState: { openCreateDialog: () => Promise<void> } & Record<string, unknown> } }).$.setupState
    await setup.openCreateDialog()
    await nextTick()
    expect(wrapper.get('.dialog').attributes('data-visible')).toBe('true')
    await nextTick()
    await wrapper.get('#list-name').setValue('Zeltlager')
    await wrapper.get('#list-description').setValue('Planung')
    await wrapper.get('#list-department').setValue('7')
    await wrapper.findAll('button').find((button) => button.text() === 'Erstellen')!.trigger('click')
    await flushPromises()

    expect(listsStore.createList).toHaveBeenCalledWith({ name: 'Zeltlager', description: 'Planung', color: '#3B82F6', department: 7 })
    expect(wrapper.get('#list-name').element).toHaveProperty('value', 'Zeltlager')
    expect(wrapper.get('#list-description').element).toHaveProperty('value', 'Planung')
    expect(wrapper.get('#list-department').element).toHaveProperty('value', '7')
    expect(wrapper.get('[role="alert"]').text()).toContain('Keine Schreibberechtigung für diese Abteilung.')
    wrapper.unmount()
  })

  it('keeps the existing department fixed when editing and includes it in the update payload', async () => {
    listsStore.lists = [existingList]
    const wrapper = render()
    await flushPromises()
    await wrapper.get('button[aria-label="pi pi-pencil"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('#list-department').element).toHaveProperty('value', '7')
    expect((wrapper.get('#list-department').element as HTMLSelectElement).disabled).toBe(true)
    await wrapper.get('#list-name').setValue('Dienstabend neu')
    await wrapper.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()

    expect(listsStore.updateList).toHaveBeenCalledWith(21, {
      name: 'Dienstabend neu', description: existingList.description, color: existingList.color, department: 7,
    })
    expect(wrapper.get('.dialog').attributes('data-visible')).toBe('false')
    wrapper.unmount()
  })
})
