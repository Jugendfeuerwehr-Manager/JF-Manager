import { describe, expect, it } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import TrainingBlockTile from '../TrainingBlockTile.vue'
import type { PlannerBlock } from '@/types/training'

const block: PlannerBlock = {
  id: 1, session: 1, title: 'Station', content: '', groups: [], groupIds: [], allGroups: true,
  library_block: null, library_block_title: null, duration_minutes: 15, start_offset_minutes: 10,
  position_order: 0, color: '', nextcloud_folder_url: '', created_at: '', updated_at: '', media: [], attachments: [],
}

describe('keyboard planning', () => {
  it('offers details but no movement or removal to read-only users', async () => {
    const wrapper = shallowMount(TrainingBlockTile, { props: { block, readOnly: true } })
    expect(wrapper.findAll('button-stub')).toHaveLength(0)
    expect(wrapper.attributes('aria-label')).toContain('Details ansehen')
    await wrapper.trigger('keydown', { key: 'ArrowDown' })
    expect(wrapper.emitted('move')).toBeUndefined()
    await wrapper.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('edit')?.[0]).toEqual([block])
  })

  it('supports movement, resizing and editing from a named focusable tile', async () => {
    const wrapper = shallowMount(TrainingBlockTile, { props: { block } })
    expect(wrapper.attributes('tabindex')).toBe('0')
    expect(wrapper.attributes('aria-label')).toContain('Station')
    await wrapper.trigger('keydown', { key: 'ArrowDown' })
    await wrapper.trigger('keydown', { key: 'ArrowUp', altKey: true, shiftKey: true })
    expect(wrapper.emitted('move')).toEqual([
      [1, { start_offset_minutes: 15 }], [1, { duration_minutes: 14 }],
    ])
    await wrapper.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('edit')?.[0]).toEqual([block])
  })

  it('does not move a block when a nested action receives an arrow key', async () => {
    const wrapper = shallowMount(TrainingBlockTile, { props: { block } })
    await wrapper.find('button-stub').trigger('keydown', { key: 'ArrowDown' })
    expect(wrapper.emitted('move')).toBeUndefined()
  })
})

describe('block colour', () => {
  it('tints the tile with a valid block colour and ignores anything else', () => {
    const coloured = shallowMount(TrainingBlockTile, { props: { block: { ...block, color: '#2563EB' } } })
    expect(coloured.attributes('style')).toContain('--tile-color: #2563eb')
    const unsafe = shallowMount(TrainingBlockTile, { props: { block: { ...block, color: 'red; background: url(x)' } } })
    expect(unsafe.attributes('style')).not.toContain('--tile-color')
    expect(unsafe.attributes('style')).not.toContain('url(')
  })

  it('shows the duration as neutral text instead of a coloured status tag', () => {
    const short = shallowMount(TrainingBlockTile, { props: { block } })
    expect(short.find('.tile-meta').text()).toBe('15 Min.')
    const long = shallowMount(TrainingBlockTile, { props: { block: { ...block, duration_minutes: 90 } } })
    expect(long.find('.tile-meta').text()).toBe('1 Std. 30 Min.')
    expect(long.find('tag-stub').exists()).toBe(false)
  })
})
