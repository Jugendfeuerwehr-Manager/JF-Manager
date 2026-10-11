import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import EmailSendReview from '../organisms/EmailSendReview.vue'
import type { EmailRecipientCheckResponse } from '@/types/emails'

const DialogStub = {
  props: ['visible'],
  template: '<div v-if="visible"><slot /><slot name="footer" /></div>',
}

const check: EmailRecipientCheckResponse = {
  count: 2,
  member_count: 3,
  personalized: true,
  merged_duplicates: 1,
  recipients: [
    { email: 'eltern@example.test', name: 'Eva Beispiel', relation: 'parent', member_id: 1, member_name: 'Ada Beispiel' },
    { email: 'eltern@example.test', name: 'Eva Beispiel', relation: 'parent', member_id: 2, member_name: 'Ben Beispiel' },
  ],
  excluded: [
    { member_id: 3, member_name: 'Cem Beispiel', email: '', relation: '', reason_code: 'no_address', reason: 'Keine E-Mail-Adresse bei Mitglied oder Eltern hinterlegt' },
    { member_id: 2, member_name: 'Ben Beispiel', email: 'kaputt', relation: 'member', reason_code: 'invalid_address', reason: 'E-Mail-Adresse ist ungültig' },
  ],
}

function mountReview(props: Partial<InstanceType<typeof EmailSendReview>['$props']> = {}) {
  return mount(EmailSendReview, {
    props: { visible: true, check, subject: 'Elternabend', previewHtml: '<p>Hallo Ada</p>', previewMemberId: 1, ...props },
    global: { plugins: [PrimeVue], stubs: { Dialog: DialogStub, Select: true } },
  })
}

describe('EmailSendReview', () => {
  it('summarises deliveries and lists every excluded person with its reason', () => {
    const wrapper = mountReview()
    const text = wrapper.text()

    expect(text).toContain('2 E-Mails werden an 3 Mitglieder')
    expect(text).toContain('2 ausgeschlossen')
    expect(text).toContain('Cem Beispiel')
    expect(text).toContain('Keine E-Mail-Adresse bei Mitglied oder Eltern hinterlegt')
    expect(text).toContain('Mitglied: kaputt')
    expect(text).toContain('E-Mail-Adresse ist ungültig')
    expect(text).toContain('1 doppelte Adresse wurde')
    expect(text).toContain('Persönliche Anrede je Mitglied')
  })

  it('renders the preview in a script-free sandboxed frame', () => {
    const frame = mountReview().get('iframe')

    expect(frame.attributes('sandbox')).toBe('')
    expect(frame.attributes('srcdoc')).toContain('Hallo Ada')
    expect(frame.attributes('srcdoc')).toContain("default-src 'none'")
  })

  it('sends only after the explicit confirmation button', async () => {
    const wrapper = mountReview()
    const send = wrapper.findAll('button').find((button) => button.text().includes('2 E-Mails senden'))

    expect(send).toBeDefined()
    await send!.trigger('click')
    expect(wrapper.emitted('send')).toHaveLength(1)
  })

  it('blocks sending when nobody would receive the message', () => {
    const wrapper = mountReview({ check: { ...check, count: 0, recipients: [] } })
    const send = wrapper.findAll('button').find((button) => button.text().includes('E-Mails senden'))

    expect(send!.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Keine Empfänger')
  })

  it('shows a retryable error instead of an empty result', async () => {
    const wrapper = mountReview({ check: null, error: 'Keine Verbindung' })

    expect(wrapper.text()).toContain('Prüfung fehlgeschlagen')
    await wrapper.findAll('button').find((button) => button.text().includes('Erneut versuchen'))!.trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
})
