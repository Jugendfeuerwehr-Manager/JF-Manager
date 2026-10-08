import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import OperationsSection from '../organisms/sections/OperationsSection.vue'

const mocks = vi.hoisted(() => ({ operations: vi.fn() }))
vi.mock('@/api/configuration', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/configuration')>()),
  configurationApi: mocks,
}))

const stubs = {
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  Button: { props: ['label'], template: '<button type="button">{{ label }}</button>' },
  Message: { props: ['severity'], template: '<div :data-severity="severity"><slot /></div>' },
  Tag: {
    props: ['value', 'severity'],
    template: '<span :data-severity="severity">{{ value }}</span>',
  },
}

async function render() {
  const wrapper = mount(OperationsSection, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('OperationsSection', () => {
  beforeEach(() => vi.clearAllMocks())

  it('explains a development installation without jfctl', async () => {
    mocks.operations.mockResolvedValue({ data: { available: false, reason: 'not_configured' } })
    const wrapper = await render()
    expect(wrapper.text()).toContain('nicht mit jfctl betrieben')
    expect(wrapper.find('dl').exists()).toBe(false)
  })

  it('shows version, backup state, workers and every warning', async () => {
    mocks.operations.mockResolvedValue({
      data: {
        available: true,
        instance: 'jf-musterstadt',
        mode: 'native',
        version: '1.4.0',
        workers_held: true,
        updated: '2026-10-07T10:00:00Z',
        last_backup: {
          status: 'failed',
          finished: '2026-10-07T03:00:00Z',
          message: 'restic backup fehlgeschlagen',
          last_success: '2026-10-05T03:00:00Z',
        },
        warnings: [
          { code: 'backup_failed', text: 'Die letzte Sicherung ist fehlgeschlagen.' },
          {
            code: 'workers_held',
            text: 'Hintergrundaufgaben sind angehalten (jfctl workers release).',
          },
        ],
      },
    })
    const wrapper = await render()
    const text = wrapper.text()
    expect(text).toContain('jf-musterstadt')
    expect(text).toContain('Debian nativ')
    expect(text).toContain('1.4.0')
    expect(text).toContain('Fehlgeschlagen')
    expect(text).toContain('restic backup fehlgeschlagen')
    expect(text).toContain('Angehalten')
    expect(wrapper.findAll('[data-severity="warn"]').length).toBeGreaterThanOrEqual(2)
  })

  it('reports a failed request without hiding the refresh action', async () => {
    mocks.operations.mockRejectedValue({
      response: {
        data: { detail: 'Der Betriebsstatus ist der Systemadministration vorbehalten.' },
      },
    })
    const wrapper = await render()
    expect(wrapper.text()).toContain('Systemadministration vorbehalten')
    expect(wrapper.text()).toContain('Aktualisieren')
  })
})
