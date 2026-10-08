import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import NotificationPreferences from '../NotificationPreferences.vue'
import { notificationPreferencesApi } from '@/api/notificationPreferences'

vi.mock('@/api/notificationPreferences', () => ({ notificationPreferencesApi: { list: vi.fn(), save: vi.fn() } }))

const rows = () => [
  { kind: 'new_sessions', label: 'Neue Dienste', email: true, push: true },
  { kind: 'assignment', label: 'Zuteilung', email: true, push: false },
]
const mountIt = async (portal = false) => {
  const w = mount(NotificationPreferences, { props: { portal }, global: { plugins: [PrimeVue] } })
  await flushPromises()
  return w
}

describe('NotificationPreferences', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(notificationPreferencesApi.list).mockResolvedValue({ data: rows() } as never)
  })

  it('renders kinds with labelled toggles and the anchor id', async () => {
    const w = await mountIt()
    expect(w.find('#mitteilungen').exists()).toBe(true)
    expect(w.text()).toContain('Neue Dienste')
    expect(w.text()).toContain('Der Eingang bleibt immer aktiv.')
    expect(w.find('input[aria-label="E-Mail für Neue Dienste"]').exists()).toBe(true)
    expect(w.find('input[aria-label="Push für Zuteilung"]').exists()).toBe(true)
  })

  it('saves on toggle', async () => {
    vi.mocked(notificationPreferencesApi.save).mockResolvedValue({ data: [{ ...rows()[0]!, email: false }, rows()[1]!] } as never)
    const w = await mountIt(true)
    expect(w.text()).toContain('standardmäßig E-Mail und Push')
    await w.find('input[aria-label="E-Mail für Neue Dienste"]').setValue(false)
    await flushPromises()
    expect(notificationPreferencesApi.save).toHaveBeenCalledWith([{ kind: 'new_sessions', email: false, push: true }])
  })

  it('reverts and shows an error when saving fails', async () => {
    vi.mocked(notificationPreferencesApi.save).mockRejectedValue(new Error('x'))
    const w = await mountIt()
    const input = w.find('input[aria-label="E-Mail für Neue Dienste"]')
    await input.setValue(false)
    await flushPromises()
    expect((w.find('input[aria-label="E-Mail für Neue Dienste"]').element as HTMLInputElement).checked).toBe(true)
    expect(w.find('[role="alert"]').exists()).toBe(true)
  })
})
