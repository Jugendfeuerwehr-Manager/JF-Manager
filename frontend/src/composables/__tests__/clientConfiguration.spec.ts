import { describe, it, expect, vi } from 'vitest'
import { useClientConfiguration } from '../useClientConfiguration'
const get = vi.hoisted(() => vi.fn())
vi.mock('@/api', () => ({ default: { get } }))
describe('Client configuration', () => {
  it('publishes only known typed defaults and vocabulary, with no credentials', async () => {
    const { configuration, refresh } = useClientConfiguration()
    get.mockResolvedValue({ data: { training_label: 'Training', default_block_duration_minutes: 30, training_start_time: 123, email_host_password: 'not-a-configuration-field' } })
    await refresh()
    expect(configuration.training_label).toBe('Training')
    expect(configuration.default_block_duration_minutes).toBe(30)
    expect(configuration.training_start_time).toBe('18:00')
    expect(configuration).not.toHaveProperty('email_host_password')
  })
  it('keeps the last valid configuration on an offline failure', async () => {
    const { configuration, refresh } = useClientConfiguration()
    const before = { ...configuration }
    get.mockRejectedValue(new Error('offline'))
    await expect(refresh()).rejects.toThrow('offline')
    expect(configuration).toEqual(before)
  })
})
