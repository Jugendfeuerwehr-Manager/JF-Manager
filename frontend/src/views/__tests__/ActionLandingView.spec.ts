import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ActionLandingView from '../ActionLandingView.vue'

const { resolve, execute, replace, route, auth, toast, hardNavigate } = vi.hoisted(() => ({
  resolve: vi.fn(), execute: vi.fn(), replace: vi.fn(), hardNavigate: vi.fn(),
  route: { params: { token: 'tok:en' } as Record<string, string> },
  auth: { isAuthenticated: true, logout: vi.fn() },
  toast: { add: vi.fn() },
}))
vi.mock('@/api/actions', () => ({ actionsApi: { resolve, execute } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ replace }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => toast }))
vi.mock('@/utils/navigation', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/utils/navigation')>()),
  hardNavigate,
}))

const render = () => mount(ActionLandingView, { global: { plugins: [PrimeVue] } })
const reply = (data: object) => ({ data })
const failure = (status: number, data: object) => Object.assign(new Error('x'), { isAxiosError: true, response: { status, data } })

const cancelPreview = {
  action: 'cancel', mode: 'confirm', state: 'ready', title: 'Vom Dienst abmelden?',
  lines: ['Übung', 'Di 14.10.2026 · 18:00', 'Mia Test'], target_route: '/portal/termine/5',
  payload_fields: [{ name: 'reason_category', type: 'choice', label: 'Grund', optional: true, choices: [{ value: 'urlaub', label: 'Urlaub' }, { value: 'krankheit', label: 'Krankheit' }] }],
}

describe('ActionLandingView', () => {
  beforeEach(() => {
    vi.clearAllMocks(); auth.isAuthenticated = true
  })

  it('sends visitors without a session to the login and back to this link', async () => {
    auth.isAuthenticated = false
    render(); await flushPromises()
    expect(replace).toHaveBeenCalledWith({ path: '/login', query: { next: '/a/tok:en' } })
    expect(resolve).not.toHaveBeenCalled()
  })

  it('runs a direct action at once and continues to the target with a toast', async () => {
    resolve.mockResolvedValue(reply({ action: 'inbox_read', mode: 'direct', state: 'ready', title: 'Hinweis als gelesen markieren', lines: [], target_route: '/eingang' }))
    execute.mockResolvedValue(reply({ action: 'inbox_read', mode: 'direct', state: 'done', message: 'Als gelesen markiert.', target_route: '/eingang' }))
    render(); await flushPromises()
    expect(resolve).toHaveBeenCalledWith('tok:en')
    expect(execute).toHaveBeenCalledWith('tok:en', {})
    expect(toast.add).toHaveBeenCalledWith(expect.objectContaining({ summary: 'Als gelesen markiert.' }))
    expect(replace).toHaveBeenCalledWith('/eingang')
  })

  it('never follows an external target route', async () => {
    resolve.mockResolvedValue(reply({ action: 'open', mode: 'direct', state: 'ready', title: 'x', lines: [], target_route: '//evil.example' }))
    execute.mockResolvedValue(reply({ action: 'open', mode: 'direct', state: 'done', target_route: '//evil.example' }))
    render(); await flushPromises()
    expect(replace).toHaveBeenCalledWith('/')
  })

  it('keeps an undoable unsubscribe on the page and can take it back', async () => {
    resolve.mockResolvedValue(reply({ action: 'unsubscribe', mode: 'direct', state: 'ready', title: 'x', lines: [], target_route: '/profile' }))
    execute.mockResolvedValueOnce(reply({ action: 'unsubscribe', mode: 'direct', state: 'done', message: 'Abbestellt.', target_route: '/profile', undo: { label: 'Rückgängig', token: 'undo-token' } }))
    execute.mockResolvedValueOnce(reply({ action: 'subscribe', mode: 'direct', state: 'done', message: 'Wieder aktiviert.', target_route: '/profile' }))
    const wrapper = render(); await flushPromises()
    expect(replace).not.toHaveBeenCalled()
    await wrapper.findAll('button').find(b => b.text() === 'Rückgängig')!.trigger('click'); await flushPromises()
    expect(execute).toHaveBeenLastCalledWith('undo-token')
    expect(wrapper.text()).toContain('Wieder aktiviert.')
  })

  it('asks for confirmation and sends the chosen reason', async () => {
    resolve.mockResolvedValue(reply(cancelPreview))
    execute.mockResolvedValue(reply({ action: 'cancel', mode: 'confirm', state: 'done', message: 'Mia ist abgemeldet.', lines: ['Übung'], target_route: '/portal/termine/5' }))
    const wrapper = render(); await flushPromises()
    expect(execute).not.toHaveBeenCalled()
    expect(wrapper.get('h1').text()).toBe('Vom Dienst abmelden?')
    expect(wrapper.text()).toContain('Mia Test')
    await wrapper.findAll('input[type=radio]')[0]!.setValue(true)
    await wrapper.findAll('button').find(b => b.text() === 'Abmelden')!.trigger('click'); await flushPromises()
    expect(execute).toHaveBeenCalledWith('tok:en', { reason_category: 'urlaub' })
    expect(wrapper.text()).toContain('Mia ist abgemeldet.')
    await wrapper.findAll('button').find(b => b.text() === 'Weiter')!.trigger('click'); await flushPromises()
    expect(replace).toHaveBeenCalledWith('/portal/termine/5')
  })

  it('leaves the confirmation without executing', async () => {
    resolve.mockResolvedValue(reply(cancelPreview))
    const wrapper = render(); await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === 'Abbrechen')!.trigger('click'); await flushPromises()
    expect(execute).not.toHaveBeenCalled()
    expect(replace).toHaveBeenCalledWith('/portal/termine/5')
  })

  it('shows the current state when the goal is already reached', async () => {
    resolve.mockResolvedValue(reply({ ...cancelPreview, state: 'done', lines: ['Bereits erledigt von Ben.'] }))
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Erledigt')
    expect(wrapper.text()).toContain('Bereits erledigt von Ben.')
    expect(execute).not.toHaveBeenCalled()
  })

  it('offers to switch accounts for a link of another account', async () => {
    resolve.mockRejectedValue(failure(403, { code: 'wrong_account', detail: 'Dieser Link gehört zu einem anderen Konto.', target_route: '/' }))
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Dieser Link gehört zu einem anderen Konto.')
    await wrapper.findAll('button').find(b => b.text() === 'Mit anderem Konto anmelden')!.trigger('click')
    expect(auth.logout).toHaveBeenCalledWith('/a/tok:en')
  })

  it.each([
    [410, 'expired', 'Link abgelaufen', 'Zur Übersicht'],
    [404, 'gone', 'Nicht mehr verfügbar', 'Zur Startseite'],
    [400, 'invalid', 'Ungültiger Link', 'Zur Startseite'],
  ])('shows a friendly page for %i %s', async (status, code, heading, button) => {
    resolve.mockRejectedValue(failure(status, { code, detail: 'Hinweis', target_route: '/portal' }))
    const wrapper = render(); await flushPromises()
    expect(wrapper.get('h1').text()).toBe(heading)
    await wrapper.findAll('button').find(b => b.text() === button)!.trigger('click'); await flushPromises()
    expect(replace).toHaveBeenCalledWith('/portal')
    expect(execute).not.toHaveBeenCalled()
  })

  it('reports a failed execution without losing the page', async () => {
    resolve.mockResolvedValue(reply(cancelPreview))
    execute.mockRejectedValue(failure(404, { code: 'gone', detail: 'Diese Aktion ist nicht mehr verfügbar.', target_route: '/portal' }))
    const wrapper = render(); await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === 'Abmelden')!.trigger('click'); await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Nicht mehr verfügbar')
  })
})
