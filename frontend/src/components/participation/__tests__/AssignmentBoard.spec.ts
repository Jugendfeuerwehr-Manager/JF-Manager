import PrimeVue from 'primevue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AssignmentBoard from '../AssignmentBoard.vue'
import { participationApi, type AssignmentBoard as Board, type BoardApplicant } from '@/api/participation'
import { useAssignmentStore } from '@/stores/assignment'

vi.mock('@/api/participation', () => ({
  participationApi: { assignment: vi.fn(), saveAssignment: vi.fn(), publishAssignment: vi.fn() },
}))
const api = vi.mocked(participationApi)
const apiError = (status: number, data: Record<string, unknown>) => Object.assign(new Error('x'), { response: { status, data } })

const person = (id: number, name: string, over: Partial<BoardApplicant> = {}): BoardApplicant => ({
  member_id: id, name, lastname: 'Test', state: 'applied', version: 1, applied_at: `2030-01-0${id}T10:00:00Z`,
  preferred_slot: null, general_ok: true, general_reasons: [], fits: [2], reasons: { 1: ['Qualifikation ‚Gruppenführer‘ fehlt'] },
  notes: [], qualifications: [], recent_assignments: 0, draft: null, published: null, conflict: false, ...over,
})
const board = (over: Partial<Board> = {}): Board => ({
  session: 7, mode: 'assignment', revision: 4, published_at: null, keep_open: false, dirty: false,
  slots: [{ id: 1, label: 'Wachführung', min: 1, max: 1, drafted: 0 }, { id: 2, label: 'Trupp', min: 1, max: 2, drafted: 0 }],
  extra_places: 0, extra_drafted: 0, staffing: { met: false, required: 2, fulfilled: 0, missing: [], text: '', slots: [] },
  applicants: [
    person(1, 'Lea', { fits: [1, 2], reasons: {}, qualifications: ['Gruppenführer'], preferred_slot: 1 }),
    person(2, 'Ole', { recent_assignments: 2 }),
    person(3, 'Ida'),
  ],
  draft: {}, ...over,
})

async function mountBoard(over: Partial<Board> = {}) {
  api.assignment.mockResolvedValue({ data: board(over) } as never)
  const wrapper = mount(AssignmentBoard, { props: { sessionId: 7, canManage: true }, global: { plugins: [PrimeVue] } })
  await flushPromises()
  return wrapper
}

const dataTransfer = () => ({ setData: vi.fn(), effectAllowed: '' })

describe('AssignmentBoard', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.resetAllMocks() })

  it('lists applications with fit, wish, chips and fairness hint and the positions with minimum', async () => {
    const wrapper = await mountBoard()
    expect(wrapper.text()).toContain('Bewerbungen (3)')
    expect(wrapper.text()).toContain('passt für: Wachführung, Trupp')
    expect(wrapper.text()).toContain('Wunsch: Wachführung')
    expect(wrapper.text()).toContain('Gruppenführer')
    expect(wrapper.text()).toContain('2× zugeteilt in 90 Tagen')
    expect(wrapper.text()).toContain('mind. 1')
    expect(wrapper.text()).toContain('Mindestbesetzung: 0 von 2 erfüllt')
  })

  it('assigns with the keyboard alternative and refuses unsuitable positions with the reason', async () => {
    const wrapper = await mountBoard()
    const select = wrapper.get('#assign-2')
    const options = select.findAll('option')
    expect(options.find(o => o.text().startsWith('Wachführung'))!.attributes('disabled')).toBeDefined()
    expect(options.find(o => o.text().startsWith('Wachführung'))!.text()).toContain('Gruppenführer‘ fehlt')
    await select.setValue('2')
    const store = useAssignmentStore()
    expect(store.draft).toEqual({ 2: 2 })
    expect(wrapper.text()).toContain('Bewerbungen (2)')
    await wrapper.get('button[aria-label="Ole Test zurück zu den Bewerbungen"]').trigger('click')
    expect(store.draft).toEqual({})
  })

  it('drags a card onto a position and greys out unsuitable positions while dragging', async () => {
    const wrapper = await mountBoard()
    const card = wrapper.findAll('article.card').find(c => c.text().includes('Ole'))!
    await card.trigger('dragstart', { dataTransfer: dataTransfer() })
    const zones = wrapper.findAll('.zone')
    expect(zones[0]!.classes()).toContain('zone--blocked')
    expect(zones[0]!.text()).toContain('Gruppenführer‘ fehlt')
    await zones[0]!.trigger('drop')
    expect(useAssignmentStore().draft).toEqual({})
    await card.trigger('dragstart', { dataTransfer: dataTransfer() })
    await zones[1]!.trigger('drop')
    expect(useAssignmentStore().draft).toEqual({ 2: 2 })
  })

  it('saves and publishes with the revision and shows a 409 conflict with both ways out', async () => {
    const wrapper = await mountBoard()
    await wrapper.get('#assign-1').setValue('1')
    api.saveAssignment.mockRejectedValue(apiError(409, { code: 'stale', current: board({ revision: 9, draft: { 3: 2 } }) }))
    await wrapper.findAll('button').find(b => b.text().includes('Entwurf speichern'))!.trigger('click')
    await flushPromises()
    expect(api.saveAssignment).toHaveBeenCalledWith(7, { revision: 4, draft: { 1: 1 } })
    expect(wrapper.text()).toContain('inzwischen von jemand anderem geändert')
    await wrapper.findAll('button').find(b => b.text().includes('Meinen Entwurf auf neuen Stand'))!.trigger('click')
    const store = useAssignmentStore()
    expect(store.draft).toEqual({ 1: 1 })
    expect(store.board!.revision).toBe(9)
    api.saveAssignment.mockResolvedValue({ data: board({ revision: 10, draft: { 1: 1 } }) } as never)
    api.publishAssignment.mockResolvedValue({ data: board({ revision: 11, draft: { 1: 1 }, published_at: '2030-01-05T10:00:00Z' }) } as never)
    expect(await store.publish(true)).toBe(true)
    expect(api.publishAssignment).toHaveBeenCalledWith(7, { revision: 10, keep_open: true })
  })

  it('is read-only without permission', async () => {
    api.assignment.mockResolvedValue({ data: board() } as never)
    const wrapper = mount(AssignmentBoard, { props: { sessionId: 7, canManage: false }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    expect(wrapper.find('#assign-1').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Zuteilung veröffentlichen')
  })
})
