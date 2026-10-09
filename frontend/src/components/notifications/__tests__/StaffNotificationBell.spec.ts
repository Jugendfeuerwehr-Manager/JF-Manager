import { defineComponent, h, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import StaffNotificationBell from '../StaffNotificationBell.vue'
import { useInboxStore } from '@/stores/inbox'
import { inboxApi, type InboxEntry } from '@/api/inbox'

vi.mock('@/api/inbox', async (orig) => ({
  ...(await orig<typeof import('@/api/inbox')>()),
  inboxApi: { list: vi.fn(), counts: vi.fn(), markRead: vi.fn() },
}))

const entry = (id: number, extra: Partial<InboxEntry> = {}): InboxEntry => ({
  id, kind: 'k', category: 'requests', type: 'notice', title: `Eintrag ${id}`, count: 1, link: `/x/${id}`, department: 'Mitte', department_id: 1,
  updated_at: new Date().toISOString(), created_at: new Date().toISOString(), read: false, task_state: null, done_by: null, done_at: null, done_via: null, ...extra,
})

const PopoverStub = defineComponent({
  emits: ['show'],
  setup(_props, { emit, slots, expose }) {
    const shown = ref(false)
    expose({
      toggle() { shown.value = !shown.value; if (shown.value) emit('show') },
      hide() { shown.value = false },
    })
    return () => (shown.value ? h('div', { class: 'popover-stub' }, slots.default?.()) : null)
  },
})
const RouterLinkStub = { props: ['to'], emits: ['click'], template: '<a :href="to" @click="$emit(\'click\')"><slot /></a>' }

function render() {
  return mount(StaffNotificationBell, { global: { stubs: { Popover: PopoverStub, RouterLink: RouterLinkStub } } })
}

describe('StaffNotificationBell', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(inboxApi.counts).mockResolvedValue({ data: { open_tasks: 0, unread_notices: 0, total: 0, by_category: {} } } as never)
    vi.mocked(inboxApi.list).mockResolvedValue({ data: { count: 0, results: [] } } as never)
    vi.mocked(inboxApi.markRead).mockResolvedValue({ data: entry(1, { read: true }) } as never)
  })

  it('shows no badge without anything open and labels the button', () => {
    const wrapper = render()
    expect(wrapper.find('.bell__badge').exists()).toBe(false)
    expect(wrapper.get('button.bell').attributes('aria-label')).toBe('Benachrichtigungen, 0 offen')
  })

  it('shows the total as badge and in the label', () => {
    useInboxStore().counts = { open_tasks: 2, unread_notices: 1, total: 3, by_category: {} }
    const wrapper = render()
    expect(wrapper.get('.bell__badge').text()).toBe('3')
    expect(wrapper.get('button.bell').attributes('aria-label')).toBe('Benachrichtigungen, 3 offen')
  })

  it('shows the empty state and the inbox link when opened without entries', async () => {
    const wrapper = render()
    await wrapper.get('button.bell').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Keine neuen Benachrichtigungen')
    expect(wrapper.get('a[href="/eingang"]').text()).toContain('Alle im Eingang')
  })

  it('summarises counts, lists the latest entries with a text marker and marks read on click', async () => {
    const summary = { open_tasks: 1, unread_notices: 1, total: 2, by_category: {} }
    vi.mocked(inboxApi.counts).mockResolvedValue({ data: summary } as never)
    vi.mocked(inboxApi.list).mockResolvedValue({
      data: { count: 7, results: [1, 2, 3, 4, 5, 6, 7].map(id => entry(id, id === 2 ? { read: true } : id === 3 ? { type: 'task', task_state: 'open' } : {})) },
    } as never)
    const wrapper = render()
    await wrapper.get('button.bell').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('1 offene Aufgabe')
    expect(wrapper.text()).toContain('1 neuer Hinweis')
    const items = wrapper.findAll('.bell-item')
    expect(items).toHaveLength(5)
    expect(items[0]!.attributes('href')).toBe('/x/1')
    expect(items[0]!.text()).toContain('Neu')
    expect(items[0]!.text()).toContain('Anträge')
    expect(items[1]!.text()).not.toContain('Neu')
    expect(items[2]!.text()).toContain('Aufgabe')
    await items[0]!.trigger('click')
    expect(inboxApi.markRead).toHaveBeenCalledWith(1)
    await items[1]!.trigger('click')
    expect(inboxApi.markRead).toHaveBeenCalledTimes(1)
  })
})
