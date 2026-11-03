import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import HealthNotesCard from '../HealthNotesCard.vue'
import { useMembersStore } from '@/stores/members'

const global = { plugins: [PrimeVue] }
// The auto-resizing textarea observes its size; jsdom has no ResizeObserver.
vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })

describe('HealthNotesCard', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('says that notes exist while they are hidden', () => {
    const wrapper = mount(HealthNotesCard, { props: { memberId: 1, hasNotes: true, canEdit: false }, global })
    expect(wrapper.text()).toContain('Angaben sind hinterlegt und ausgeblendet.')
    expect(wrapper.text()).not.toContain('Keine Angaben')
  })

  it('still knows about notes saved here after hiding them again', async () => {
    const store = useMembersStore()
    vi.spyOn(store, 'fetchHealthNotes').mockResolvedValue(true)
    vi.spyOn(store, 'saveHealthNotes').mockImplementation(async (id, text) => {
      store.healthNotes = { ...store.healthNotes, [id]: text }
      return true
    })
    const wrapper = mount(HealthNotesCard, { props: { memberId: 1, hasNotes: false, canEdit: true }, global })
    expect(wrapper.text()).toContain('Keine Angaben hinterlegt.')

    await wrapper.findAll('button').find((b) => b.text().includes('Erfassen'))!.trigger('click')
    await flushPromises()
    await wrapper.find('textarea').setValue('Wespenallergie')
    await wrapper.findAll('button').find((b) => b.text().includes('Speichern'))!.trigger('click')
    await flushPromises()
    expect(wrapper.find('.health-card__value').text()).toBe('Wespenallergie')

    await wrapper.findAll('button').find((b) => b.text().includes('Ausblenden'))!.trigger('click')
    expect(wrapper.text()).toContain('Angaben sind hinterlegt und ausgeblendet.')
  })
})
