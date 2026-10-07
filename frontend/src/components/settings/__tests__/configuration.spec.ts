import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ConfigurationSection from '../organisms/sections/ConfigurationSection.vue'
import SetupSection from '../organisms/sections/SetupSection.vue'
import { configurationError } from '@/api/configuration'
const mocks = vi.hoisted(() => ({
  catalog: vi.fn(),
  get: vi.fn(),
  update: vi.fn(),
  generatePushKeys: vi.fn(),
  setup: vi.fn(),
}))
vi.mock('@/api/configuration', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/configuration')>()),
  configurationApi: mocks,
}))
vi.mock('@/composables/useClientConfiguration', () => ({
  useClientConfiguration: () => ({ refresh: vi.fn().mockResolvedValue(undefined) }),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ hasPerm: () => true }) }))
vi.mock('vue-router', () => ({ onBeforeRouteLeave: vi.fn(), onBeforeRouteUpdate: vi.fn() }))
const field = (label: string, extra = {}) => ({
  label,
  type: 'integer',
  secret: false,
  source: 'default',
  storage: 'database',
  locked: false,
  allow_blank: false,
  effective: 'Neue Datensätze',
  validation: '',
  ...extra,
})
const stubs = {
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  Button: {
    props: ['label', 'disabled', 'type'],
    template:
      '<button :disabled="disabled" :type="type || \'button\'"><slot />{{ label }}</button>',
  },
  Message: { template: '<div role="status"><slot /></div>' },
}
async function render(kind = 'training') {
  const wrapper = mount(ConfigurationSection, { props: { kind }, global: { stubs } })
  await flushPromises()
  return wrapper
}
beforeEach(() => {
  vi.clearAllMocks()
  mocks.catalog.mockResolvedValue({
    data: {
      categories: {
        training: {
          label: 'Übungsstandards',
          can_change: true,
          fields: { default_block_duration_minutes: field('Bausteindauer') },
        },
      },
      host: [],
    },
  })
  mocks.get.mockResolvedValue({ data: { default_block_duration_minutes: 15 } })
})
describe('Configuration editor', () => {
  it('preserves edits and reports an API failure without claiming success', async () => {
    const wrapper = await render()
    await wrapper.get('input').setValue('30')
    mocks.update.mockRejectedValue({ response: { data: { detail: 'Speichern fehlgeschlagen' } } })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.update).toHaveBeenCalledWith('training', { default_block_duration_minutes: 30 })
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('30')
    expect(wrapper.text()).toContain('Speichern fehlgeschlagen')
    expect(wrapper.text()).not.toContain('Einstellungen gespeichert.')
  })
  it('uses the returned server state after saving and updates the displayed source', async () => {
    const wrapper = await render()
    await wrapper.get('input').setValue('30')
    mocks.update.mockResolvedValue({ data: { default_block_duration_minutes: 30 } })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Einstellungen gespeichert.')
    expect(wrapper.text()).toContain('Organisationseinstellung')
    expect(
      wrapper
        .findAll('button')
        .find((button) => button.text() === 'Speichern')
        ?.attributes('disabled'),
    ).toBeDefined()
  })
  it('shows environment locks and excludes locked and unchanged secret fields from partial updates', async () => {
    mocks.catalog.mockResolvedValue({
      data: {
        categories: {
          push: {
            label: 'Push',
            can_change: true,
            fields: {
              public_key: field('Öffentlich', {
                type: 'string',
                source: 'environment',
                locked: true,
              }),
              private_key: field('Privat', {
                type: 'string',
                secret: true,
                source: 'environment',
                locked: true,
              }),
              subject: field('Kontakt', { type: 'string', source: 'environment', locked: true }),
              enabled: field('Aktiviert', { type: 'boolean' }),
            },
          },
        },
      },
    })
    mocks.get.mockResolvedValue({
      data: {
        public_key: 'public',
        subject: 'mailto:admin@example.org',
        enabled: true,
        has_private_key: true,
      },
    })
    const wrapper = await render('push')
    expect(wrapper.text()).toContain('Hostkonfiguration')
    expect(wrapper.get('#config-private_key').attributes('disabled')).toBeDefined()
    expect((wrapper.get('#config-private_key').element as HTMLInputElement).value).toBe('')
    await wrapper.get('#config-enabled').setValue(false)
    mocks.update.mockResolvedValue({ data: { enabled: false, has_private_key: true } })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.update).toHaveBeenCalledWith('push', { enabled: false })
    expect(mocks.generatePushKeys).not.toHaveBeenCalled()
  })
})
describe('Readable session durations', () => {
  it('converts displayed days and minutes to canonical server seconds', async () => {
    mocks.catalog.mockResolvedValue({
      data: {
        categories: {
          security: {
            label: 'Sitzungen',
            can_change: true,
            fields: {
              session_idle_timeout_seconds: field('Zeit ohne Aktivität (Sekunden)', {
                min: 300,
                max: 7776000,
              }),
            },
          },
        },
      },
    })
    mocks.get.mockResolvedValue({ data: { session_idle_timeout_seconds: 2592000 } })
    const wrapper = await render('security')
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('30')
    await wrapper.get('select').setValue('minutes')
    await wrapper.get('input').setValue('10')
    mocks.update.mockResolvedValue({ data: { session_idle_timeout_seconds: 600 } })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.update).toHaveBeenCalledWith('security', { session_idle_timeout_seconds: 600 })
  })
})
describe('Setup guide', () => {
  it('loads status without writes and connects all five setup steps to actual web administration', async () => {
    mocks.setup.mockResolvedValue({
      data: {
        organization_configured: false,
        active_departments: 0,
        standard_roles: 16,
        expected_standard_roles: 16,
        administrator_assigned: false,
      },
    })
    const wrapper = mount(SetupSection, { global: { stubs } })
    await flushPromises()
    for (const text of [
      'Organisation',
      'Abteilungen',
      'Konten und Rollen',
      'Standards',
      'Integrationen',
    ])
      expect(wrapper.text()).toContain(text)
    await wrapper.findAll('nav button')[2]!.trigger('click')
    expect(wrapper.text()).toContain('16 von 16 Standardrollen')
    expect(wrapper.find('a[href="/role-templates"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/roles"]').exists()).toBe(true)
    await wrapper.findAll('nav button')[4]!.trigger('click')
    expect(wrapper.find('a[href="/settings/security"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/settings/push"]').exists()).toBe(true)
    expect(mocks.update).not.toHaveBeenCalled()
  })
})

describe('Readable configuration errors', () => {
  it('explains cancelled step-up without showing internal protocol codes', () => {
    expect(
      configurationError({
        response: {
          data: {
            detail: 'Bitte die Änderung erneut bestätigen.',
            code: 'reauthentication_required',
          },
        },
      }),
    ).toBe('Bitte die Änderung erneut bestätigen.')
  })
})
