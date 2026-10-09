import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LibraryBlockPicker from '../LibraryBlockPicker.vue'
import { useLibraryStore } from '@/stores/library'

const block = {
  id: 7, title: 'Knoten und Stiche', default_duration_minutes: 25, category: 2, category_name: 'Technik',
  category_color: '#ffff00', color: '', last_used_date: null, description: 'Mastwurf, Kreuzknoten und Halbschlag üben.',
  usage_count: 4, tags: [1, 2, 3, 4, 5].map((id) => ({ id, name: `Tag ${id}` })),
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

  it('shows description, usage and tags and keeps dragging into a lane', async () => {
    const wrapper = mount()
    await flushPromises()
    const item = wrapper.get('.picker-item')
    const description = item.get('.picker-item-description')
    expect(description.text()).toBe('Mastwurf, Kreuzknoten und Halbschlag üben.')
    expect(item.attributes('aria-describedby')).toBe(description.attributes('id'))
    expect(item.get('.picker-usage').text()).toBe('4 × verwendet')
    expect(item.findAll('.picker-item-tags li').map((li) => li.text())).toEqual(['Tag 1', 'Tag 2', 'Tag 3', 'Tag 4', '+1'])

    expect(item.attributes('draggable')).toBe('true')
    const data = new Map<string, string>()
    await item.trigger('dragstart', { dataTransfer: { setData: (k: string, v: string) => data.set(k, v), setDragImage: () => {} } })
    expect(data.get('application/x-library-block-id')).toBe('7')
    expect(data.get('application/x-library-block-duration')).toBe('25')
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
