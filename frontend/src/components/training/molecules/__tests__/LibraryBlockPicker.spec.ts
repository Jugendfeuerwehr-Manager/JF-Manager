import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LibraryBlockPicker from '../LibraryBlockPicker.vue'
import { useLibraryStore } from '@/stores/library'

const block = {
  id: 7, title: 'Knoten und Stiche', default_duration_minutes: 25, category: 2, category_name: 'Technik',
  category_color: '#ffff00', color: '', last_used_date: null,
}

function mount() {
  return shallowMount(LibraryBlockPicker, { global: { directives: { tooltip: () => {} }, stubs: { RouterLink: true, IconField: { template: '<div><slot /></div>' } } } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  const store = useLibraryStore()
  vi.spyOn(store, 'fetchBlocks').mockResolvedValue(undefined as never)
  vi.spyOn(store, 'fetchCategories').mockResolvedValue(undefined as never)
  vi.spyOn(store, 'fetchTags').mockResolvedValue(undefined as never)
  store.blocks = [block] as never
})

describe('library sidebar', () => {
  it('lets keyboard users insert a block', async () => {
    const wrapper = mount()
    await flushPromises()
    const item = wrapper.get('.picker-item')
    expect(item.attributes('role')).toBe('button')
    expect(item.attributes('tabindex')).toBe('0')
    expect(item.attributes('aria-label')).toBe('Knoten und Stiche einfügen')
    await item.trigger('keydown', { key: 'Enter' })
    await item.trigger('keydown', { key: ' ' })
    expect(wrapper.emitted('pick')).toEqual([[block], [block]])
  })

  it('names its icon-only controls and filters', async () => {
    const wrapper = mount()
    await flushPromises()
    expect(wrapper.find('[aria-label="Bibliothek schließen"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Bibliothek verwalten (neuer Tab)"]').exists()).toBe(true)
    for (const label of ['Bausteine durchsuchen', 'Kategorie', 'Tags']) {
      expect(wrapper.find(`[aria-label="${label}"]`).exists(), label).toBe(true)
    }
  })
})
