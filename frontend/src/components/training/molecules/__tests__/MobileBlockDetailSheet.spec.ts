import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import MobileBlockDetailSheet from '../MobileBlockDetailSheet.vue'
import type { PlannerBlock } from '@/types/training'

vi.mock('@/api/training', () => ({
  trainingBlocksApi: { listMedia: vi.fn().mockResolvedValue({ data: [] }) },
}))

afterEach(() => {
  document.body.innerHTML = ''
})

describe('MobileBlockDetailSheet rich text', () => {
  it('does not keep encoded script URLs from stored training content', async () => {
    const block = {
      id: 1,
      title: 'Übung',
      content: '<p><a href="java&#x73;cript:alert(1)">Info</a></p>',
      session: 1,
      groups: [],
      groupIds: [],
      allGroups: true,
      library_block: null,
      library_block_title: null,
      start_offset_minutes: 0,
      duration_minutes: 30,
      position_order: 0,
      color: '#123456',
      nextcloud_folder_url: '',
      created_at: '',
      updated_at: '',
      media: [],
      attachments: [],
    } satisfies PlannerBlock
    const wrapper = mount(MobileBlockDetailSheet, {
      props: { block, sessionStartMin: 600 },
      attachTo: document.body,
    })
    await flushPromises()

    const link = document.querySelector<HTMLAnchorElement>('.sheet-content a')
    expect(link).not.toBeNull()
    expect(link?.getAttribute('href')).not.toMatch(/^javascript:/i)
    wrapper.unmount()
  })
})
