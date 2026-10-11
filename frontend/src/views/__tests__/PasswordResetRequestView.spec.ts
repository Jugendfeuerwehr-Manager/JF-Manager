import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import PasswordResetRequestView from '../PasswordResetRequestView.vue'

const { requestPasswordReset } = vi.hoisted(() => ({ requestPasswordReset: vi.fn() }))
vi.mock('@/api/auth', () => ({ authApi: { requestPasswordReset } }))

function render() {
  return mount(PasswordResetRequestView, {
    global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })
}

describe('PasswordResetRequestView (DES-01.11)', () => {
  it('asks for an address and confirms without revealing whether an account exists', async () => {
    requestPasswordReset.mockResolvedValue({})
    const wrapper = render()
    expect(wrapper.get('h1').text()).toBe('Passwort zurücksetzen')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[role="alert"]').text()).toContain('Bitte gib deine E-Mail-Adresse ein')
    await wrapper.get('#email').setValue('person@example.test')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(requestPasswordReset).toHaveBeenCalledWith('person@example.test')
    expect(wrapper.get('[role="status"]').text()).toContain('Falls ein Konto mit dieser E-Mail-Adresse existiert')
  })
})
