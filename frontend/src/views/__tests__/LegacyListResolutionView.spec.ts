import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import LegacyListResolutionView from '../LegacyListResolutionView.vue'

const { pending, resolve, targets, push } = vi.hoisted(() => ({ pending: vi.fn(), resolve: vi.fn(), targets: vi.fn(), push: vi.fn() }))
const user = { is_superuser: true }
const departmentStore = {
  departments: [{ id: 7, name: 'Jugend', is_active: true }],
  error: null as string | null,
  fetchDepartments: vi.fn(),
}
vi.mock('@/api/legacy-list-resolution', () => ({ legacyListResolutionApi: { pending, resolve, targets } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user }) }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => departmentStore }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

const source = {
  id: 42,
  name: 'Sommerfahrt',
  description: 'Bitte vertraulich behandeln',
  entries: [{ id: 81, member_id: 10, member_name: 'Max Beispiel', department_ids: [7], checked: true, checked_at: null, notes: 'Notiz', added_at: '' }],
  attachments: [{ id: 90, name: 'Plan.pdf', description: 'Fahrtplan', file_size: 2048, mime_type: 'application/pdf' }],
  targets: [],
}

function render() {
  return mount(LegacyListResolutionView, {
    global: {
      stubs: {
        Button: { props: ['label'], template: '<button @click="$emit(\'click\')">{{ label }}</button>' },
        Checkbox: {
          props: { modelValue: null, value: null, binary: Boolean, disabled: Boolean },
          template: '<input type="checkbox" :checked="binary ? modelValue : modelValue?.includes(value)" :disabled="disabled" @change="$emit(\'update:modelValue\', binary ? $event.target.checked : ($event.target.checked ? [...(modelValue || []), value] : (modelValue || []).filter(item => item !== value)))">',
        },
        Message: { template: '<div><slot /></div>' },
        ProgressSpinner: true,
        Select: {
          props: ['id', 'modelValue', 'options', 'optionLabel', 'optionValue', 'placeholder', 'disabled'],
          template: '<select :id="id" :value="modelValue ?? \'\'" :disabled="disabled" @change="$emit(\'update:modelValue\', $event.target.value ? Number($event.target.value) : null)"><option value="">{{ placeholder }}</option><option v-for="option in options" :key="option[optionValue]" :value="option[optionValue]">{{ option[optionLabel] }}</option></select>',
        },
        Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
      },
    },
  })
}

describe('LegacyListResolutionView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    pending.mockResolvedValue({ data: [source] })
    targets.mockResolvedValue({ data: { results: [{ id: 501, name: 'Sommerfahrt Jugend', department: 7 }], next: null } })
    resolve.mockResolvedValue({ data: { target_list_id: 501, complete: false, pending: { ...source, description: '', entries: [], attachments: [], targets: [{ department: 7, list_id: 501 }] } } })
    departmentStore.error = null
  })

  it('shows the source, membership choices, possible departments, description and attachment metadata', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Sommerfahrt')
    expect(wrapper.text()).toContain('Bitte vertraulich behandeln')
    expect(wrapper.text()).toContain('Max Beispiel')
    expect(wrapper.text()).toContain('Jugend')
    expect(wrapper.text()).toContain('Plan.pdf')
    expect(wrapper.text()).toContain('application/pdf')
    expect(wrapper.text()).toContain('Quelle abschließen')
    wrapper.unmount()
  })

  it('explains a forbidden or failed pending-list request', async () => {
    pending.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'Keine Berechtigung.' } } })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Berechtigung.')
    expect(wrapper.text()).not.toContain('Es gibt keine offenen Altlisten.')
    wrapper.unmount()
  })

  it('submits selected entries with an explicitly chosen existing destination list', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#department-42').setValue('7')
    await flushPromises()
    await wrapper.get('#target-42').setValue('501')
    await wrapper.findAll('input[type="checkbox"]')[0]!.setValue(true)
    await wrapper.findAll('button').find((button) => button.text().includes('Ausgewählte Inhalte zuordnen'))!.trigger('click')
    await flushPromises()
    expect(targets).toHaveBeenCalledWith(7, 1)
    expect(resolve).toHaveBeenCalledWith(42, expect.objectContaining({ department: 7, target_list_id: 501, entry_ids: [81], complete: false }))
    wrapper.unmount()
  })

  it('requires the explicit completion action and confirmation for an empty source', async () => {
    const emptySource = { ...source, id: 43, description: '', entries: [], attachments: [] }
    pending.mockResolvedValueOnce({ data: [emptySource] })
    resolve.mockResolvedValueOnce({ data: { target_list_id: 502, complete: true, pending: null } })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#department-43').setValue('7')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('Quelle abschließen'))!.trigger('click')
    await flushPromises()
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('endgültig abschließen'))
    expect(resolve).toHaveBeenCalledWith(43, expect.objectContaining({ department: 7, complete: true, entry_ids: [], attachment_ids: [] }))
    expect(wrapper.text()).not.toContain('Sommerfahrt')
    confirm.mockRestore()
    wrapper.unmount()
  })

  it('keeps a previously bound destination fixed', async () => {
    pending.mockResolvedValueOnce({ data: [{ ...source, targets: [{ department: 7, list_id: 501 }] }] })
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#department-42').setValue('7')
    await flushPromises()
    expect(wrapper.text()).toContain('Zielliste #501 fest gebunden')
    expect(wrapper.find('#target-42').exists()).toBe(false)
    wrapper.unmount()
  })

  it('shows target-list loading failures without presenting them as an empty list result', async () => {
    targets.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'Ziellistenzugriff verweigert.' } } })
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#department-42').setValue('7')
    await flushPromises()
    expect(wrapper.text()).toContain('Ziellistenzugriff verweigert.')
    expect(wrapper.text()).not.toContain('Keine bestehende Zielliste gefunden')
    wrapper.unmount()
  })
})
