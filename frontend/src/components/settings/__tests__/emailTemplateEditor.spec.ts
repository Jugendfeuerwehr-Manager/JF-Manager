import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import EmailTemplateEditor from '../organisms/EmailTemplateEditor.vue'
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import { useWorkspaceNavigation } from '@/composables/useWorkspaceNavigation'

const mocks = vi.hoisted(() => ({
  api: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    getTypes: vi.fn(),
    getVariables: vi.fn(),
    preview: vi.fn(),
    getDefaultContent: vi.fn(),
  },
  router: { push: vi.fn(), replace: vi.fn() },
  leaveGuards: [] as Array<() => boolean>,
}))

vi.mock('@/api/email-templates', () => ({ emailTemplatesApi: mocks.api }))
vi.mock('vue-router', () => ({
  useRouter: () => mocks.router,
  onBeforeRouteLeave: (guard: () => boolean) => mocks.leaveGuards.push(guard),
}))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

const stubs = {
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
  Button: {
    props: ['label', 'disabled', 'ariaLabel'],
    template: '<button :disabled="disabled" :aria-label="ariaLabel"><slot />{{ label }}</button>',
  },
  Message: { template: '<div role="status"><slot /></div>' },
  Select: {
    props: ['modelValue', 'options', 'optionValue', 'id'],
    emits: ['update:modelValue'],
    template:
      '<select :id="id" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option></select>',
  },
  ToggleSwitch: { template: '<input type="checkbox" />' },
  InputText: {
    props: ['modelValue', 'id'],
    emits: ['update:modelValue'],
    template: '<input :id="id" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  MonacoEditor: {
    props: ['modelValue', 'language'],
    emits: ['update:modelValue'],
    template: '<textarea :data-language="language" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  PhoneMockup: { props: ['subject'], template: '<div class="phone">{{ subject }}</div>' },
}

const template = {
  id: 7,
  name: 'Erinnerung',
  template_type: 'participation_reminder',
  template_type_display: 'Teilnahme-Erinnerung',
  subject_template: 'Erinnerung {{ service.date }}',
  html_template: '<p>Hallo</p>',
  text_template: '',
  layout: 'none',
  layout_display: 'Kein Layout',
  is_active: true,
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-02T10:00:00Z',
}

function render(templateId: number | null) {
  return mount(EmailTemplateEditor, {
    props: { templateId },
    global: { stubs, directives: { tooltip: {} } },
  })
}

function saveButton(wrapper: ReturnType<typeof render>) {
  return wrapper.findAll('button').find((b) => b.text() === 'Speichern')!
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mocks.leaveGuards.length = 0
  mocks.api.list.mockResolvedValue({ data: { results: [template] } })
  mocks.api.getTypes.mockResolvedValue({
    data: [
      { value: 'participation_reminder', label: 'Teilnahme-Erinnerung' },
      { value: 'portal_invitation', label: 'Portal-Einladung' },
    ],
  })
  mocks.api.get.mockResolvedValue({ data: template })
  mocks.api.getVariables.mockResolvedValue({
    data: { template_type: 'participation_reminder', variables: [{ name: 'member', type: 'Mitglied', description: 'Empfänger' }], sample_data: {} },
  })
  mocks.api.preview.mockResolvedValue({ data: { subject: 'Erinnerung 12.10.', html_content: '<p>Hallo</p>', text_content: '', errors: [] } })
})

describe('EmailTemplateEditor', () => {
  it('opens an existing template as a workspace with live preview', async () => {
    const wrapper = render(7)
    await flushPromises()

    expect(wrapper.find('h1').text()).toBe('Teilnahme-Erinnerung')
    expect(wrapper.text()).toContain('Alles gespeichert')
    expect(wrapper.find('.phone').text()).toBe('Erinnerung 12.10.')
    expect(saveButton(wrapper).attributes('disabled')).toBeDefined()
    expect(wrapper.find('[aria-label="Navigation ausblenden, mehr Platz zum Bearbeiten"]').exists()).toBe(true)
  })

  it('saves changes in place and keeps the editor open', async () => {
    mocks.api.update.mockResolvedValue({ data: { ...template, subject_template: 'Neu' } })
    const wrapper = render(7)
    await flushPromises()

    await wrapper.get('#subject').setValue('Neu')
    expect(wrapper.text()).toContain('Ungespeicherte Änderungen')
    expect(mocks.leaveGuards[0]).toBeDefined()

    await wrapper.trigger('keydown', { key: 's', ctrlKey: true })
    await flushPromises()

    expect(mocks.api.update).toHaveBeenCalledWith(7, expect.objectContaining({ subject_template: 'Neu' }))
    expect(mocks.router.push).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Alles gespeichert')
  })

  it('asks before leaving with unsaved changes', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = render(7)
    await flushPromises()
    const guard = mocks.leaveGuards[0]!

    expect(guard()).toBe(true)
    await wrapper.get('#subject').setValue('Neu')
    expect(guard()).toBe(false)
    expect(confirmSpy).toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('switches between HTML and plain text content', async () => {
    const wrapper = render(7)
    await flushPromises()
    expect(wrapper.get('textarea').attributes('data-language')).toBe('html')

    await wrapper.findAll('button').find((b) => b.text() === 'Nur Text')!.trigger('click')
    expect(wrapper.get('textarea').attributes('data-language')).toBe('plaintext')
  })

  it('creates a template from the default content of the chosen type', async () => {
    mocks.api.getDefaultContent.mockResolvedValue({
      data: { subject_template: 'Einladung', html_template: '<p>Willkommen</p>', text_template: 'Willkommen' },
    })
    mocks.api.create.mockResolvedValue({ data: { ...template, id: 12, template_type: 'portal_invitation' } })
    const wrapper = render(null)
    await flushPromises()

    expect(wrapper.text()).toContain('Welche E-Mail soll die Vorlage ersetzen?')
    // Only types without an own template can be chosen.
    expect(wrapper.findAll('#template-type-step option').map((o) => o.text())).toEqual(['Portal-Einladung'])

    await wrapper.get('#template-type-step').setValue('portal_invitation')
    await flushPromises()

    expect((wrapper.get('#name').element as HTMLInputElement).value).toBe('Portal-Einladung')
    await saveButton(wrapper).trigger('click')
    await flushPromises()

    expect(mocks.api.create).toHaveBeenCalledWith(expect.objectContaining({ template_type: 'portal_invitation', subject_template: 'Einladung' }))
    expect(mocks.router.replace).toHaveBeenCalledWith({ name: 'email-template-edit', params: { id: 12 } })
  })
})

describe('WorkspaceHeader', () => {
  it('toggles the shared navigation visibility', async () => {
    const { setNavHidden, navHidden } = useWorkspaceNavigation()
    setNavHidden(false)
    const wrapper = mount(WorkspaceHeader, {
      props: { title: 'Vorlage', backTo: '/settings', backLabel: 'Einstellungen' },
      global: { stubs, directives: { tooltip: {} } },
    })

    await wrapper.get('button').trigger('click')
    expect(navHidden.value).toBe(true)
    expect(wrapper.get('button').attributes('aria-label')).toBe('Navigation einblenden')
    setNavHidden(false)
  })
})
