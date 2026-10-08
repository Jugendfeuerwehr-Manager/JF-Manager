import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import TrainingRun from '../TrainingRun.vue'
import { useAuthStore } from '@/stores/auth'

const station = (id: number, title: string, start: number, group: { id: number; name: string }, extra = {}) => ({
  id, title, session: 1, groups: [group], content: '<p>Zeigen, üben</p>', duration_minutes: 25, start_offset_minutes: start,
  position_order: 0, library_block: null, library_block_title: null, color: '', nextcloud_folder_url: '', media: [],
  attachments: [], kind: 'station', station_key: title, location: 'Halle', instructors: [], materials: [], ...extra,
})
const toni = { id: 7, name: 'Toni Trainer' }
let revision = 3
let status = 'published'
const plan = vi.fn(async () => ({ data: {
  id: 1, revision, status, title: 'Stationsabend', date: '2026-10-11', start_time: '18:00:00', end_time: '20:00:00',
  description: '', notes: '', location: '', department: 1, groups: [], linked_service_id: 12, can_manage_plan: false,
  blocks: [
    station(1, 'Knoten', 0, { id: 1, name: 'Bambini' }, { instructors: [toni], safety_notes: 'Handschuhe', materials: [{ item: null, variant: null, quantity: 4, label: 'Leinen' }] }),
    station(2, 'Schlauch', 0, { id: 2, name: 'Jugend' }),
    station(3, 'Knoten', 30, { id: 2, name: 'Jugend' }, { instructors: [toni] }),
    station(4, 'Schlauch', 30, { id: 1, name: 'Bambini' }),
  ],
} }))
vi.mock('@/api/training', () => ({ trainingSessionsApi: { plan: () => plan() } }))
vi.mock('vue-router', async (importOriginal) => ({ ...(await importOriginal<typeof import('vue-router')>()), useRouter: () => ({ back: vi.fn(), push: vi.fn() }) }))

const stubs = {
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
  SafeHtml: { props: ['html'], template: '<div v-html="html" />' },
  Button: { props: ['label', 'ariaLabel', 'disabled'], emits: ['click'], template: '<button :aria-label="ariaLabel" :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
}

async function mountAt(hour: number, minute: number) {
  vi.setSystemTime(new Date(2026, 9, 11, hour, minute))
  setActivePinia(createPinia())
  useAuthStore().user = { id: 7 } as never
  const wrapper = mount(TrainingRun, { props: { sessionId: 1 }, global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('TrainingRun', () => {
  beforeEach(() => { vi.useFakeTimers({ toFake: ['Date'] }); localStorage.clear(); revision = 3; status = 'published' })
  afterEach(() => { vi.useRealTimers() })

  it('shows the current round with remaining time and every station', async () => {
    const wrapper = await mountAt(18, 7)
    const hero = wrapper.find('.run__hero').text()
    expect(hero).toContain('Jetzt · Runde 1 von 2')
    expect(hero).toContain('noch 18 Min.')
    expect(hero).toContain('18:00–18:25')
    expect(hero).toContain('Danach: Übergang ab 18:25')
    const cards = wrapper.findAll('.run__card').map((c) => c.text())
    expect(cards[0]).toContain('Knoten')
    expect(cards[0]).toContain('Bambini')
    expect(cards[0]).toContain('danach Jugend')
    expect(cards[0]).toContain('Toni Trainer')
    expect(wrapper.text()).toContain('Plan Version 3')
    expect(wrapper.find('.run__header').text()).toContain('Läuft')
  })

  it('shows the own station with procedure, safety and a device-only checklist', async () => {
    const wrapper = await mountAt(18, 7)
    await wrapper.findAll('button').find((b) => b.text() === 'Meine Station')!.trigger('click')
    const mine = wrapper.find('.run__mine')
    expect(mine.text()).toContain('Deine Station')
    expect(mine.text()).toContain('Jetzt Bambini · danach Jugend · Halle')
    expect(mine.text()).toContain('Zeigen, üben')
    expect(mine.text()).toContain('Handschuhe')
    expect(mine.text()).toContain('nur auf diesem Gerät')
    await mine.find('input[type="checkbox"]').setValue(true)
    expect(JSON.parse(localStorage.getItem('jf-run-materials:1:Knoten')!)).toEqual([0])
  })

  it('browses sections without saving and returns to the clock', async () => {
    const wrapper = await mountAt(18, 7)
    await wrapper.find('[aria-label="Nächster Abschnitt"]').trigger('click')
    await wrapper.find('[aria-label="Nächster Abschnitt"]').trigger('click')
    expect(wrapper.find('.run__hero').text()).toContain('Ansicht · Runde 2 von 2')
    await wrapper.findAll('button').find((b) => b.text() === 'Zur aktuellen Zeit')!.trigger('click')
    expect(wrapper.find('.run__hero').text()).toContain('Jetzt · Runde 1 von 2')
  })

  it('announces start, end, offline state and a newer plan version', async () => {
    expect((await mountAt(17, 15)).find('.run__hero').text()).toContain('Beginnt in 45 Min.')
    const wrapper = await mountAt(19, 30)
    expect(wrapper.find('.run__hero').text()).toContain('Übung beendet')
    window.dispatchEvent(new Event('offline'))
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Verbindung')
    revision = 4
    window.dispatchEvent(new Event('online'))
    await flushPromises()
    expect(wrapper.text()).toContain('auf Version 4 aktualisiert')
    wrapper.unmount()
  })

  it('shows the stored status instead of the clock for cancelled exercises', async () => {
    status = 'cancelled'
    const wrapper = await mountAt(18, 7)
    expect(wrapper.find('.run__header').text()).toContain('Abgesagt')
    expect(wrapper.find('.run__header').text()).not.toContain('Läuft')
    expect(wrapper.find('[role="alert"]').text()).toContain('abgesagt')
  })

  it('does not count down a completed exercise', async () => {
    status = 'completed'
    const wrapper = await mountAt(18, 7)
    const hero = wrapper.find('.run__hero').text()
    expect(hero).toContain('Übung abgeschlossen')
    expect(hero).not.toContain('noch')
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(false)
  })
})
