import ToastService from 'primevue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { id: 1 } }) }))
vi.mock('interactjs',() => ({ default: () => ({
  draggable: (config: unknown) => { mocks.draggable(config); return { resizable: mocks.resizable } },
  unset: mocks.unset,
}) }))

function mount() {
  return shallowMount(SwimlaneEditor, { props: { sessionId: 1 }, global: {
    directives: { tooltip: () => {} }, stubs: { RouterLink: true }, plugins: [ToastService],
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

const headerStubs = {
  WorkspaceHeader: { props: ['title', 'eyebrow'], template: '<header class="ws-stub"><h1>{{ title }}</h1><p class="eyebrow">{{ eyebrow }}</p><slot name="meta" /><slot name="status" /><div class="actions"><slot name="actions" /></div></header>' },
  Button: { props: ['label', 'ariaLabel', 'disabled'], emits: ['click'], template: '<button type="button" :aria-label="ariaLabel" :disabled="disabled" @click="$emit(\'click\', $event)">{{ label }}</button>' },
  Menu: { props: ['model'], template: '<ul class="menu-stub"><li v-for="item in model" :key="item.key" :data-disabled="item.disabled">{{ item.label }}</li></ul>' },
}

function mountAt(width: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
  return shallowMount(SwimlaneEditor, { props: { sessionId: 1 }, global: {
    directives: { tooltip: () => {} }, stubs: { RouterLink: true, ...headerStubs }, plugins: [ToastService],
  } })
}

describe('planner header', () => {
  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 })
    localStorage.clear()
  })

  it('shows one main action, the save state and a menu on phones', async () => {
    const wrapper = mountAt(390)
    await flushPromises()
    const buttons = wrapper.findAll('.actions > button')
    expect(buttons.map((b) => b.attributes('aria-label') ?? b.text())).toEqual(['Weitere Aktionen', 'Speichern'])
    expect(wrapper.get('[role="status"]').text()).toBe('Gespeichert')
    const menu = wrapper.findAll('.menu-stub li').map((li) => li.text())
    expect(menu).toEqual(expect.arrayContaining(['Rückgängig', 'Wiederholen', 'Bibliothek', 'Baustein', 'Rotation', 'Planaktion', 'Teilnahme', 'Handout', 'Einstellungen der Übung', 'Auf anderes Datum kopieren', 'Absagen']))
    expect(wrapper.get('h1').text()).toBe('Testplan')

    useTrainingPlannerStore().stageMove(1, { start_offset_minutes: 30 })
    await flushPromises()
    expect(wrapper.get('[role="status"]').text()).toBe('Ungespeichert')
    expect(wrapper.findAll('.menu-stub li').find((li) => li.text().startsWith('Auf anderes Datum'))!.text()).toBe('Auf anderes Datum kopieren (zuerst speichern)')
    wrapper.unmount()
  })

  it('shows planning tools as buttons on wide screens and keeps cancelling in the menu', async () => {
    const wrapper = mountAt(1700)
    await flushPromises()
    const labels = wrapper.findAll('.actions > button').map((b) => b.attributes('aria-label') ?? b.text())
    expect(labels).toEqual(expect.arrayContaining(['Rückgängig', 'Bibliothek schließen', 'Baustein', 'Rotation', 'Planaktion', 'Teilnahme', 'Speichern']))
    expect(labels).not.toContain('Absagen')
    expect(wrapper.findAll('.menu-stub li').map((li) => li.text())).toContain('Absagen')
    expect(wrapper.get('[role="status"]').text()).toBe('Alles gespeichert')
    wrapper.unmount()
  })
})

describe('planner library panel', () => {
  it('reopens with the remembered width and resizes from the keyboard', async () => {
    localStorage.setItem('jf-planner-library:1', JSON.stringify({ width: 500, open: true }))
    const wrapper = mount()
    await flushPromises()
    const panel = wrapper.get('.library-panel')
    expect(panel.attributes('style')).toContain('--library-width: 500px')
    const separator = panel.get('[role="separator"]')
    expect(separator.attributes('aria-label')).toBe('Breite der Bibliothek')
    expect(separator.attributes('tabindex')).toBe('0')
    expect(separator.attributes('aria-controls')).toBe('planner-library')
    await separator.trigger('keydown', { key: 'ArrowLeft' })
    expect(separator.attributes('aria-valuenow')).toBe('516')
    expect(JSON.parse(localStorage.getItem('jf-planner-library:1')!)).toEqual({ width: 516, open: true })
    wrapper.unmount()
    localStorage.clear()
  })
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
