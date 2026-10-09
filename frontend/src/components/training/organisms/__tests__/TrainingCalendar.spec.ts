import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'
import type { TrainingSessionList } from '@/types/training'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: vi.fn() }) }))

const trainingStore = reactive({
  sessions: [] as TrainingSessionList[],
  loading: false,
  error: null as string | null,
  fetchSessions: vi.fn(),
  deleteSession: vi.fn(),
})
vi.mock('@/stores/training', () => ({ useTrainingStore: () => trainingStore }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ hasPerm: () => true }) }))
vi.mock('@/stores/departments', () => ({
  useDepartmentsStore: () => ({ activeDepartmentId: 1, departments: [{ id: 1, code: 'JF', name: 'Jugendfeuerwehr', color: '#c62828' }] }),
}))

import TrainingCalendar from '../TrainingCalendar.vue'

function session(overrides: Partial<TrainingSessionList>): TrainingSessionList {
  return {
    status: 'published', id: 1, title: 'Knotenkunde', date: '2026-10-14', start_time: '18:00:00', end_time: '20:00:00',
    location: 'Gerätehaus', group_count: 0, groups: [], block_count: 0, department: 1, linked_service_id: null,
    linked_service_start: null, requires_service_confirmation: false, can_manage_plan: true, series_parent: null,
    series_uuid: null, original_date: null, recurrence_rule: null, ...overrides,
  }
}

function mountCalendar() {
  return mount(TrainingCalendar, {
    global: {
      stubs: {
        Dialog: { props: ['visible', 'header'], template: '<div v-if="visible" class="dialog-stub"><h3>{{ header }}</h3><slot /><slot name="footer" /></div>' },
        Button: { props: ['label', 'ariaLabel'], emits: ['click'], template: '<button type="button" class="p-button" :aria-label="ariaLabel" @click="$emit(\'click\', $event)">{{ label }}</button>' },
        InputText: true,
        TrainingSessionForm: true,
        SeriesDialog: true,
        TrainingTemplatesDialog: true,
      },
    },
  })
}

describe('TrainingCalendar', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 9, 9, 12))
    push.mockReset()
    trainingStore.fetchSessions.mockReset().mockResolvedValue(undefined)
    trainingStore.error = null
    trainingStore.sessions = [
      session({ id: 1 }),
      session({ id: 2, title: 'Abgesagte Übung', status: 'cancelled', date: '2026-10-17', start_time: '10:00:00' }),
    ]
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders only the weeks of the month in a fluid seven-column grid', async () => {
    const wrapper = mountCalendar()
    await flushPromises()
    // October 2026 starts on a Thursday and spans five Monday-based weeks.
    expect(wrapper.findAll('.cal-cell')).toHaveLength(35)
    expect(wrapper.findAll('.cal-weekday')).toHaveLength(7)
    expect(wrapper.findAll('.cal-cell.is-weekend')).toHaveLength(10)
    expect(trainingStore.fetchSessions).toHaveBeenCalledWith({ date_from: '2026-09-01', date_to: '2026-11-30', limit: 200 })
  })

  it('marks today with aria-current and labels each day for keyboard users', async () => {
    const wrapper = mountCalendar()
    await flushPromises()
    const today = wrapper.find('.cal-cell.today button.cell-day')
    expect(today.attributes('aria-current')).toBe('date')
    expect(today.attributes('aria-label')).toContain('(heute)')
    await today.trigger('click')
    expect(wrapper.find('.dialog-stub h3').text()).toBe('Freitag, 9. Oktober')
  })

  it('shows time, title and status on event chips with the full text as label', async () => {
    const wrapper = mountCalendar()
    await flushPromises()
    const chips = wrapper.findAll('button.session-pill')
    expect(chips).toHaveLength(2)
    expect(chips[0]!.find('.session-pill__time').text()).toBe('18:00')
    expect(chips[0]!.attributes('aria-label')).toBe('18:00 · Knotenkunde · Veröffentlicht · JF')
    expect(chips[0]!.attributes('title')).toBe(chips[0]!.attributes('aria-label'))
    expect(chips[1]!.classes()).toContain('session-pill--cancelled')
    expect(chips[1]!.attributes('aria-label')).toContain('Abgesagt')
    expect(chips[0]!.attributes('style')).toContain('--session-accent: #c62828')

    await chips[0]!.trigger('click')
    expect(push).toHaveBeenCalledWith('/training/sessions/1/plan')
    expect(wrapper.find('.dialog-stub').exists()).toBe(false)
  })

  it('offers one primary action and switches to the list through the segmented control', async () => {
    const wrapper = mountCalendar()
    await flushPromises()
    expect(wrapper.find('.cal-actions').text()).toContain('Übung erstellen')
    const listButton = wrapper.findAll('.segmented button').find((b) => b.text() === 'Liste')!
    await listButton.trigger('click')
    await flushPromises()
    expect(trainingStore.fetchSessions).toHaveBeenLastCalledWith({ limit: 500 })
    expect(wrapper.find('.cal-grid').exists()).toBe(false)
    expect(wrapper.findAll('.list-session-item')).toHaveLength(2)
  })
})
