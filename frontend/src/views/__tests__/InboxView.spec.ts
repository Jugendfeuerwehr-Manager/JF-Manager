import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import InboxView from '../InboxView.vue'
import { inboxApi, type InboxEntry } from '@/api/inbox'
import { useInboxStore } from '@/stores/inbox'

vi.mock('@/api/inbox', async (orig) => ({
  ...(await orig<typeof import('@/api/inbox')>()),
  inboxApi: { list: vi.fn(), counts: vi.fn(), markRead: vi.fn(), markReadBulk: vi.fn(), markDone: vi.fn() },
}))
const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => ({ departments: [{ id: 1, name: 'Mitte' }, { id: 2, name: 'Nord' }], fetchDepartments: vi.fn() }) }))

const entry = (id: number, extra: Partial<InboxEntry> = {}): InboxEntry => ({
  id, kind: 'k', category: 'requests', type: 'task', title: `Titel ${id}`, count: 1, link: `/anträge/${id}`, department: 'Mitte', department_id: 1,
  updated_at: new Date().toISOString(), created_at: new Date().toISOString(), read: true, task_state: 'open', done_by: null, done_at: null, done_via: null, ...extra,
})
const render = () => mount(InboxView, { global: { stubs: { Select: true } } })

describe('InboxView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(inboxApi.counts).mockResolvedValue({ data: { open_tasks: 1, unread_notices: 1, total: 2 } } as never)
    vi.mocked(inboxApi.list).mockResolvedValue({ data: { count: 0, results: [] } } as never)
  })

  it('shows an empty state without entries', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Alles erledigt')
    expect(wrapper.text()).toContain('1 offene Aufgabe · 1 ungelesene Hinweis')
  })

  it('renders open tasks, done tasks and bundled unread notices', async () => {
    vi.mocked(inboxApi.list).mockResolvedValue({ data: { count: 3, results: [
      entry(1),
      entry(2, { task_state: 'done', done_by: 'A. Keller', done_via: 'email_action', done_at: new Date().toISOString() }),
      entry(3, { type: 'notice', task_state: null, read: false, count: 3, category: 'registrations', title: '3 Abmeldungen · Knoten und Stiche' }),
    ] } } as never)
    const wrapper = render()
    await flushPromises()
    const cards = wrapper.findAll('.inbox-card')
    expect(cards).toHaveLength(3)
    expect(cards[0]!.text()).toContain('Aufgabe')
    expect(cards[0]!.text()).toContain('Als erledigt markieren')
    expect(cards[1]!.text()).toMatch(/Erledigt von A\. Keller heute \d\d:\d\d per E-Mail-Aktion/)
    expect(cards[1]!.text()).not.toContain('Als erledigt markieren')
    expect(cards[2]!.text()).toContain('Hinweis')
    expect(cards[2]!.text()).toContain('Ungelesen:')
    expect(cards[2]!.text()).toContain('3 Meldungen gebündelt')
    expect(cards[2]!.find('.inbox-dot').exists()).toBe(true)
  })

  it('changes the query when filter chips are used', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text().startsWith('Aufgaben'))!.trigger('click')
    expect(inboxApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'task' }))
    await wrapper.findAll('button').find(b => b.text().startsWith('Besetzung'))!.trigger('click')
    expect(inboxApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'task', category: 'staffing' }))
    await wrapper.findAll('input[type=checkbox]')[1]!.setValue(true)
    expect(inboxApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ done: true }))
    await flushPromises()
    expect(wrapper.text()).toContain('Keine passenden Einträge')
  })

  it('opens an unread entry after marking it read, and marks tasks done', async () => {
    vi.mocked(inboxApi.list).mockResolvedValue({ data: { count: 2, results: [entry(1, { read: false }), entry(2)] } } as never)
    vi.mocked(inboxApi.markRead).mockResolvedValue({ data: entry(1, { read: true }) } as never)
    vi.mocked(inboxApi.markDone).mockResolvedValue({ data: entry(2, { task_state: 'done' }) } as never)
    const wrapper = render()
    await flushPromises()
    const cards = wrapper.findAll('.inbox-card')
    await cards[0]!.findAll('button').find(b => b.text() === 'Öffnen')!.trigger('click')
    await flushPromises()
    expect(inboxApi.markRead).toHaveBeenCalledWith(1)
    expect(push).toHaveBeenCalledWith('/anträge/1')
    await cards[1]!.findAll('button').find(b => b.text() === 'Als erledigt markieren')!.trigger('click')
    await flushPromises()
    expect(inboxApi.markDone).toHaveBeenCalledWith(2)
    expect(wrapper.findAll('.inbox-card')).toHaveLength(1)
    expect(useInboxStore().entries).toHaveLength(1)
  })

  it('marks the selected entries as read', async () => {
    vi.mocked(inboxApi.list).mockResolvedValue({ data: { count: 1, results: [entry(5, { type: 'notice', task_state: null, read: false })] } } as never)
    vi.mocked(inboxApi.markReadBulk).mockResolvedValue({ data: { updated: 1 } } as never)
    const wrapper = render()
    await flushPromises()
    await wrapper.get('.inbox-select').setValue(true)
    await wrapper.findAll('button').find(b => b.text().includes('Als gelesen markieren'))!.trigger('click')
    await flushPromises()
    expect(inboxApi.markReadBulk).toHaveBeenCalledWith([5])
    expect(wrapper.find('.inbox-dot').exists()).toBe(false)
  })
})
