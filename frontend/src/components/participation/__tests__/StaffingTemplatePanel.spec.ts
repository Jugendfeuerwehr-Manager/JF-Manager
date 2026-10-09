import PrimeVue from 'primevue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import StaffingTemplatePanel from '../StaffingTemplatePanel.vue'
import TemplateStaffingPicker from '../TemplateStaffingPicker.vue'
import { participationApi, staffingTemplatesApi, type ParticipationConfig, type StaffingTemplate } from '@/api/participation'
import { useParticipationStore } from '@/stores/participation'

vi.mock('@/api/participation', () => ({
  participationApi: { config: vi.fn(), saveConfig: vi.fn(), registrations: vi.fn(), preview: vi.fn() },
  staffingTemplatesApi: { list: vi.fn(), create: vi.fn(), archive: vi.fn(), apply: vi.fn(), trainingTemplate: vi.fn(), setTrainingTemplate: vi.fn() },
}))
const api = vi.mocked(participationApi)
const tplApi = vi.mocked(staffingTemplatesApi)

const config = (over: Partial<ParticipationConfig> = {}) => ({
  session: 7, revision: 3, mode: 'opt_in', portal_visible: true, public_note: '', registration_opens_at: null,
  registration_closes_at: null, cancellation_closes_at: null, max_participants: 10, min_participants: null, waitlist_mode: 'auto',
  eligibility: {}, effective: { start: '', registration_opens_at: null, registration_closes_at: '', cancellation_closes_at: '' },
  defaults: { mode: 'opt_out', registration_offset_h: 48, cancellation_offset_h: 2, waitlist_mode: 'auto' },
  eligibility_summary: null, audience_notice: null, extra_places: null, slots: [], capacity: 10, staffing: null, department: 2, ...over,
}) as ParticipationConfig
const template = (over: Partial<StaffingTemplate> = {}): StaffingTemplate => ({
  id: 5, name: 'Brandsicherheitswache', description: '', department: 2, department_name: 'Mitte', scope: 'department', version: 1,
  archived: false, archived_at: null, updated_at: '', mode: 'opt_in', slots: [{ label: 'Wachführung', min: 1, max: 1 }], summary: null, ...over,
})

async function mountPanel() {
  api.config.mockResolvedValue({ data: config() } as never)
  tplApi.list.mockResolvedValue({ data: { results: [template(), template({ id: 6, name: 'Org', scope: 'organization', department: null })], can_manage_organization: false } } as never)
  const store = useParticipationStore()
  await store.loadConfig(7)
  const wrapper = mount(StaffingTemplatePanel, { props: { sessionId: 7, department: 2 }, global: { plugins: [PrimeVue] } })
  await flushPromises()
  return { wrapper, store }
}

describe('StaffingTemplatePanel', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.resetAllMocks() })

  it('applies a template after confirmation and shows warnings and the source', async () => {
    const { wrapper, store } = await mountPanel()
    expect(tplApi.list).toHaveBeenCalledWith({ department: 2, archived: false })
    expect(wrapper.text()).toContain('Org (Organisation)')
    await wrapper.get('#tpl-select').setValue('5')
    expect(wrapper.text()).toContain('Wachführung (1/1)')
    tplApi.apply.mockResolvedValue({ data: { ...config({ revision: 4, template_source: { id: 5, name: 'Brandsicherheitswache' } }), warnings: ['Qualifikation #9 gibt es nicht mehr und wurde entfernt.'] } } as never)
    await wrapper.findAll('button').find(b => b.text() === 'Anwenden')!.trigger('click')
    await flushPromises()
    const confirm = document.body.querySelectorAll('button')
    const apply = Array.from(confirm).filter(b => b.textContent?.includes('Anwenden')).at(-1) as HTMLButtonElement
    apply.click()
    await flushPromises()
    expect(tplApi.apply).toHaveBeenCalledWith(7, 5, 3)
    expect(store.config?.revision).toBe(4)
    expect(wrapper.text()).toContain('gibt es nicht mehr')
    expect(wrapper.text()).toContain('Übernommen aus „Brandsicherheitswache“')
    wrapper.unmount()
  })

  it('saves the current service as a department template (organisation locked without right)', async () => {
    const { wrapper } = await mountPanel()
    tplApi.create.mockResolvedValue({ data: template({ id: 9, name: 'Neu' }) } as never)
    await wrapper.findAll('button').find(b => b.text().includes('Als Vorlage speichern'))!.trigger('click')
    await flushPromises()
    const name = document.body.querySelector('#tpl-name') as HTMLInputElement
    name.value = 'Neu'
    name.dispatchEvent(new Event('input'))
    await flushPromises()
    const org = document.body.querySelector('input[value="organization"]') as HTMLInputElement
    expect(org.disabled).toBe(true)
    const save = Array.from(document.body.querySelectorAll('button')).find(b => b.textContent?.trim() === 'Speichern') as HTMLButtonElement
    save.click()
    await flushPromises()
    expect(tplApi.create).toHaveBeenCalledWith({ name: 'Neu', description: '', department: 2, session: 7 })
    expect(wrapper.text()).toContain('Als Vorlage „Neu“ gespeichert')
    wrapper.unmount()
  })
})

describe('TemplateStaffingPicker', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.resetAllMocks() })

  it('stores a staffing template on an exercise template', async () => {
    tplApi.trainingTemplate.mockResolvedValue({ data: { staffing_template: null, name: null, mode: null, slots: [] } } as never)
    tplApi.list.mockResolvedValue({ data: { results: [template()], can_manage_organization: false } } as never)
    tplApi.setTrainingTemplate.mockResolvedValue({ data: { staffing_template: 5, name: 'Brandsicherheitswache', mode: 'opt_in', slots: [{ label: 'Wachführung', min: 1, max: 1 }] } } as never)
    const wrapper = mount(TemplateStaffingPicker, { props: { templateId: 3, department: 2, title: 'Knoten' }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Besetzung hinterlegt')
    await wrapper.get('select').setValue('5')
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(tplApi.setTrainingTemplate).toHaveBeenCalledWith(3, 5)
    expect(wrapper.text()).toContain('Aktuell: Brandsicherheitswache · Wachführung (1/1)')
  })
})
