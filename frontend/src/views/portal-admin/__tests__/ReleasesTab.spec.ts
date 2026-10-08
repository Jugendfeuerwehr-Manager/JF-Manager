import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ReleasesTab from '../ReleasesTab.vue'
import { portalAdminApi, type PolicyOverview } from '@/api/portalAdmin'

vi.mock('@/api/portalAdmin', () => ({ portalAdminApi: { policies: vi.fn(), savePolicy: vi.fn() } }))

function overview(editable = true): PolicyOverview {
  return {
    categories: [
      { key: 'contact', label: 'Kontakt', hint: 'Name und Anschrift', fixed: true, audiences: ['parents', 'members'] },
      { key: 'swimming', label: 'Schwimmfähigkeit', hint: 'Ja oder nein', fixed: false, audiences: ['parents', 'members'] },
      { key: 'other_parents', label: 'Weitere Eltern', hint: 'Nur für Eltern', fixed: false, audiences: ['parents'] },
    ],
    never_visible: 'Anwesenheiten und Notizen sind nie sichtbar.',
    organization: {
      editable, version: 1, member_portal_mode: 'off', member_portal_min_age: null,
      effective: { swimming: { parents: 'visible', members: 'hidden' }, other_parents: { parents: 'hidden' } },
      ceiling: { swimming: { parents: 'allowed', members: 'locked' }, other_parents: { parents: 'allowed' } },
    },
    departments: [{
      id: 5, name: 'Mitte', editable, version: 2, member_portal_mode: 'min_age', member_portal_min_age: 10,
      overrides: {}, effective: { swimming: { parents: 'visible', members: 'hidden' }, other_parents: { parents: 'hidden' } },
      locked: { swimming: { parents: false, members: true }, other_parents: { parents: false } },
      member_portal: { mode: 'min_age', min_age: 10, eligible: 14, missing_birthday: 3 },
    }],
  }
}

async function render(data = overview()) {
  vi.mocked(portalAdminApi.policies).mockResolvedValue({ data } as never)
  const wrapper = mount(ReleasesTab, { global: { stubs: {
    Button: { props: ['label', 'disabled'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
    Select: { name: 'Select', props: ['modelValue', 'options'], emits: ['update:modelValue'], template: '<div class="scope-stub">{{ options.flatMap(g => g.items.map(i => i.label + (i.deviates ? \' (weicht ab)\' : \'\'))).join(\'|\') }}</div>' },
  } } })
  await flushPromises()
  return wrapper
}
const scopeButton = (w: Awaited<ReturnType<typeof render>>, text: string) => w.findAll('button').find(b => b.text().includes(text))!

describe('ReleasesTab', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('renders fixed, not-applicable and editable cells for the organisation', async () => {
    const w = await render()
    expect(w.find('[data-cell="contact.parents"]').text()).toContain('immer')
    expect(w.find('[data-cell="other_parents.members"]').text()).toBe('–')
    expect(w.find('[data-cell="swimming.parents"]').text()).toContain('sichtbar')
    expect(w.find('[data-cell="swimming.parents"]').text()).toContain('für Abteilungen sperren')
    expect(w.text()).toContain('Anwesenheiten und Notizen sind nie sichtbar.')
    expect(w.text()).toContain('Keine Mitgliederkonten')
    expect(scopeButton(w, 'Speichern').attributes('disabled')).toBeDefined()
  })

  it('shows locked cells, stats and the inherit option in a department', async () => {
    const w = await render()
    w.findComponent({ name: 'Select' }).vm.$emit('update:modelValue', '5')
    await flushPromises()
    expect(w.find('[data-cell="swimming.members"]').text()).toContain('gesperrt')
    expect(w.find('[data-cell="swimming.members"] .pi-lock').exists()).toBe(true)
    expect(w.find('[data-cell="swimming.parents"]').text()).toContain('Wie Organisation (sichtbar)')
    expect(w.text()).toContain('Betrifft 14 Mitglieder in Mitte.')
    expect(w.text()).toContain('(3 Mitglieder)')
    expect(w.text()).toContain('Wie Organisation')
  })

  it('enables saving after an edit and saves with the version', async () => {
    const w = await render()
    await w.find('[data-cell="swimming.parents"] .segmented button:last-child').trigger('click')
    const save = scopeButton(w, 'Speichern')
    expect(save.attributes('disabled')).toBeUndefined()
    vi.mocked(portalAdminApi.savePolicy).mockResolvedValue({ data: overview() } as never)
    await save.trigger('click')
    await flushPromises()
    expect(portalAdminApi.savePolicy).toHaveBeenCalledWith('org', { version: 1, visibility: { swimming: { parents: 'hidden' } } })
    expect(w.text()).toContain('gespeichert')
  })

  it('shows a field error at the cell', async () => {
    const w = await render()
    await w.find('[data-cell="swimming.parents"] .segmented button:last-child').trigger('click')
    vi.mocked(portalAdminApi.savePolicy).mockRejectedValue(Object.assign(new Error('x'), { response: { status: 400, data: { 'swimming.parents': ['Nicht erlaubt.'] } } }))
    await scopeButton(w, 'Speichern').trigger('click')
    await flushPromises()
    expect(w.find('[data-cell="swimming.parents"]').text()).toContain('Nicht erlaubt.')
  })

  it('renders read-only without controls or save buttons', async () => {
    const w = await render(overview(false))
    expect(w.find('[data-cell="swimming.parents"] .segmented').exists()).toBe(false)
    expect(w.text()).toContain('nicht ändern')
    expect(w.findAll('button').some(b => b.text() === 'Speichern')).toBe(false)
  })

  it('offers a searchable scope list that flags deviating departments', async () => {
    const data = overview()
    data.departments.push({ ...data.departments[0]!, id: 6, name: 'Nord', member_portal_mode: '', overrides: {} })
    const w = await render(data)
    expect(w.find('.scope-stub').text()).toBe('Organisation (Vorgaben)|Mitte (weicht ab)|Nord')
    expect(w.text()).toContain('1 Abteilung weicht von den Vorgaben ab.')
  })
})
