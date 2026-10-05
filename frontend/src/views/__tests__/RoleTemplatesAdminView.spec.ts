import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RoleTemplatesAdminView from '../RoleTemplatesAdminView.vue'

const { list, compare, update, applyPermissions, archive, duplicate } = vi.hoisted(() => ({
  list: vi.fn(), compare: vi.fn(), update: vi.fn(), applyPermissions: vi.fn(), archive: vi.fn(), duplicate: vi.fn(),
}))
vi.mock('@/api/role-templates', () => ({ roleTemplatesApi: { list, compare, update, applyPermissions, archive, duplicate } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ hasPerm: () => true }) }))

const template = { id: 1, key: 'leader', name: 'Leitung', description: 'Leitung', template_version: 1,
  scope: 'organization', is_delegable: true, is_archived: false, group: { id: 10, name: 'Leitung' } }
const comparison = { ...template, actual_permissions: ['members.view_member'], expected_permissions: ['members.view_member'],
  expected_metadata: null, metadata_differences: null, missing_permissions: [], extra_permissions: [],
  assignment_counts: { global_users: 2, staff_users: 0, department_roles: 0, ldap_mappings: 0, oidc_mappings: 0 },
  fingerprint: 'current-fingerprint' }

function render() {
  return mount(RoleTemplatesAdminView, { global: { stubs: {
    Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
    Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
    Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /></div>' },
    InputText: { props: ['modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)">' },
    Textarea: { props: ['modelValue'], template: '<textarea :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
    Message: { template: '<div><slot /></div>' }, ProgressSpinner: true,
    Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
  } } })
}

function button(wrapper: ReturnType<typeof render>, label: string) {
  return wrapper.findAll('button').find((element) => element.text().includes(label))!
}

describe('RoleTemplatesAdminView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    list.mockResolvedValue({ data: { count: 1, next: null, results: [template] } })
    compare.mockResolvedValue({ data: comparison })
    update.mockResolvedValue({ data: template })
    applyPermissions.mockResolvedValue({ data: comparison })
    archive.mockResolvedValue({ data: { ...template, is_archived: true } })
    duplicate.mockResolvedValue({ data: { ...template, id: 2 } })
  })

  it('loads all pages and shows the comparison with assignment counts', async () => {
    list.mockResolvedValueOnce({ data: { count: 2, next: '/next', results: [template] } })
      .mockResolvedValueOnce({ data: { count: 2, next: null, results: [{ ...template, id: 2, name: 'Stellvertretung' }] } })
    const wrapper = render()
    await flushPromises()
    expect(list).toHaveBeenNthCalledWith(1, 0)
    expect(list).toHaveBeenNthCalledWith(2, 1)
    expect(wrapper.text()).toContain('Stellvertretung')
    expect(wrapper.text()).toContain('Fehlende Rechte')
    expect(wrapper.text()).toContain('2Konten')
    wrapper.unmount()
  })

  it('adds another qualified permission and sends the full selection with the comparison fingerprint', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.get('[aria-label="Berechtigung hinzufügen"]').setValue('orders.view_order')
    await button(wrapper, 'Recht hinzufügen').trigger('click')
    await button(wrapper, 'Auswahl prüfen und übernehmen').trigger('click')
    await flushPromises()
    expect(applyPermissions).toHaveBeenCalledWith(1, {
      fingerprint: 'current-fingerprint', permissions: ['members.view_member', 'orders.view_order'],
    })
    wrapper.unmount()
  })

  it('retains unsaved metadata after a stale comparison response', async () => {
    update.mockRejectedValueOnce({ response: { status: 409, data: { detail: 'Vergleich veraltet.' } } })
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#role-name').setValue('Neue Leitung')
    await button(wrapper, 'Metadaten speichern').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith(1, expect.objectContaining({ fingerprint: 'current-fingerprint', name: 'Neue Leitung' }))
    expect(wrapper.text()).toContain('Vergleich veraltet.')
    expect((wrapper.get('#role-name').element as HTMLInputElement).value).toBe('Neue Leitung')
    wrapper.unmount()
  })

  it('requires confirmation for archive and duplicate actions', async () => {
    const wrapper = render()
    await flushPromises()
    await button(wrapper, 'Archivieren').trigger('click')
    await flushPromises()
    expect(archive).toHaveBeenCalledWith(1, 'current-fingerprint')
    await button(wrapper, 'Vorlage kopieren').trigger('click')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(duplicate).toHaveBeenCalledWith(1, expect.objectContaining({ key: 'leader_copy', fingerprint: 'current-fingerprint' }))
    expect(window.confirm).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })
})
