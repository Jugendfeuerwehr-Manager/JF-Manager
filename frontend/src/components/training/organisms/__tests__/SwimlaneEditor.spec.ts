import { beforeEach, describe, expect, it, vi } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SwimlaneEditor from '../SwimlaneEditor.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'

const mocks = vi.hoisted(() => ({
  plan: vi.fn(), draggable: vi.fn(), resizable: vi.fn(), unset: vi.fn(),
  leave: undefined as (() => boolean) | undefined,
  update: undefined as (() => boolean) | undefined,
}))
vi.mock('@/api/training', () => ({ trainingSessionsApi: { plan: mocks.plan } }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  onBeforeRouteLeave: (handler: () => boolean) => { mocks.leave = handler },
  onBeforeRouteUpdate: (handler: () => boolean) => { mocks.update = handler },
}))
vi.mock('interactjs', () => ({ default: () => ({
  draggable: (config: unknown) => { mocks.draggable(config); return { resizable: mocks.resizable } },
  unset: mocks.unset,
}) }))

function mount() {
  return shallowMount(SwimlaneEditor, { props: { sessionId: 1 }, global: {
    directives: { tooltip: () => {} }, stubs: { RouterLink: true },
  } })
}

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
  const block = (id: number) => ({ id, title: `Block ${id}`, session: 1, groups: [],
    content: '', duration_minutes: 15, start_offset_minutes: 0, position_order: 0,
    library_block: null, color: '', nextcloud_folder_url: '', media: [], attachments: [],
  })
  mocks.plan.mockResolvedValue({ data: {
    id: 1, revision: 1, title: 'Testplan', date: '2030-01-01', start_time: '18:00:00', end_time: '20:00:00',
    description: '', location: '', notes: '', department: 1, groups: [], recurrence_rule: null,
    blocks: [block(1), block(2)],
  } })
})

describe('planner navigation and gestures', () => {
  it('guards route changes and browser exit while retaining a rejected departure', async () => {
    const wrapper = mount()
    await flushPromises()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    expect(mocks.leave!()).toBe(true)
    expect(confirm).not.toHaveBeenCalled()
    const store = useTrainingPlannerStore()
    store.stageMove(1, { start_offset_minutes: 30 })
    expect(mocks.leave!()).toBe(false)
    expect(mocks.update!()).toBe(false)
    expect(store.isDirty).toBe(true)
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    wrapper.unmount()
    const afterUnmount = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(afterUnmount)
    expect(afterUnmount.defaultPrevented).toBe(false)
    expect(store.session).toBeNull()
    confirm.mockRestore()
  })

  it('dragging into an occupied period never swaps another block', async () => {
    const wrapper = mount()
    await flushPromises()
    const listeners = mocks.draggable.mock.calls[0]![0].listeners
    const target = document.createElement('div')
    target.dataset.blockId = '1'
    target.style.top = '0px'
    listeners.start({ target })
    listeners.move({ target, dy: 20, client: { x: -1000 } })
    listeners.end({ target })
    const store = useTrainingPlannerStore()
    expect(store.blocks[0]!.start_offset_minutes).toBe(5)
    expect(store.blocks[1]!.start_offset_minutes).toBe(0)
    store.undo()
    expect(store.blocks[0]!.start_offset_minutes).toBe(0)
    expect(store.canUndo).toBe(false)
    wrapper.unmount()
  })
})
