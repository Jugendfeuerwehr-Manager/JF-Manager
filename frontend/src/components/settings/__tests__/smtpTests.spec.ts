import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SMTPTestPanel from '../molecules/SMTPTestPanel.vue'
const post = vi.hoisted(() => vi.fn())
vi.mock('@/api', () => ({ default: { post } }))
const stubs = {
  Button: {
    props: ['label', 'disabled'],
    template: '<button :disabled="disabled">{{ label }}</button>',
  },
  Message: { template: '<p><slot /></p>' },
}
describe('Explicit SMTP tests', () => {
  it('separates connection testing from an explicitly confirmed test message', async () => {
    post.mockResolvedValue({ data: { ok: true, detail: 'synthetic-test-result' } })
    const wrapper = mount(SMTPTestPanel, { props: { canEdit: true }, global: { stubs } })
    await wrapper.findAll('button')[0]!.trigger('click')
    await flushPromises()
    expect(post).toHaveBeenLastCalledWith('/settings/email/test-connection/', {})
    expect(wrapper.findAll('button')[1]!.attributes('disabled')).toBeDefined()
    await wrapper.get('input[type=email]').setValue('synthetic@example.org')
    expect(wrapper.findAll('button')[1]!.attributes('disabled')).toBeDefined()
    await wrapper.get('input[type=checkbox]').setValue(true)
    await wrapper.findAll('button')[1]!.trigger('click')
    await flushPromises()
    expect(post).toHaveBeenLastCalledWith('/settings/email/send-test/', {
      recipient: 'synthetic@example.org',
      confirm_send: true,
    })
    expect(wrapper.findAll('button')[1]!.attributes('disabled')).toBeDefined()
  })
})
