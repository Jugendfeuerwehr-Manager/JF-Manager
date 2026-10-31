import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import HealthNotesCard from '../organisms/HealthNotesCard.vue'
import { membersApi } from '@/api/members'

vi.mock('@/api/members', () => ({ membersApi: { health: vi.fn(), saveHealth: vi.fn() } }))

const render = (props: { hasNotes: boolean, canEdit: boolean }) => mount(HealthNotesCard, {
  props: { memberId: 5, ...props },
  global: { plugins: [PrimeVue] },
})

describe('HealthNotesCard', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('loads the text only on explicit request', async () => {
    vi.mocked(membersApi.health).mockResolvedValue({ data: { health_notes: 'Allergie: Wespenstich' } } as never)
    const wrapper = render({ hasNotes: true, canEdit: false })
    expect(membersApi.health).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('Wespenstich')
    await wrapper.get('button').trigger('click'); await flushPromises()
    expect(membersApi.health).toHaveBeenCalledWith(5)
    expect(wrapper.text()).toContain('Allergie: Wespenstich')
    const hide = wrapper.findAll('button').find(b => b.text() === 'Ausblenden')!
    await hide.trigger('click')
    expect(wrapper.text()).not.toContain('Wespenstich')
  })

  it('shows the server refusal instead of data', async () => {
    vi.mocked(membersApi.health).mockRejectedValue({ response: { status: 403, data: { detail: 'Keine Berechtigung für Gesundheitsangaben.' } } })
    const wrapper = render({ hasNotes: true, canEdit: false })
    await wrapper.get('button').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Keine Berechtigung für Gesundheitsangaben.')
  })
})
