import { describe, expect, it } from 'vitest'
import { buildApplicationPdf, buildVoucherCardPdf } from '../admissionPdf'
import type { FormSchema } from '@/types/admissions'

const schema: FormSchema = {
  pages: [
    {
      id: 'p',
      title: 'Personalien',
      sections: [
        {
          id: 's',
          title: 'Person',
          elements: [
            { id: 'a', type: 'text', key: 'vorname', label: 'Vorname' },
            { id: 'g', type: 'select', key: 'geschlecht', label: 'Geschlecht', target: 'member.gender' },
            { id: 'u', type: 'signature', key: 'unterschrift', role: 'applicant', label: 'Unterschrift' }
          ]
        }
      ]
    }
  ]
}

describe('admission PDFs', () => {
  it('prints answers, signature lines and the seal with a QR code', () => {
    const doc = buildApplicationPdf({
      title: 'Aufnahmeantrag', department: 'Mitte', schema, answers: { vorname: 'Mia', geschlecht: 'female' }, images: {},
      signatureMode: 'both', seal: { publicId: 'abc123xyz', sealHash: 'f'.repeat(64), label: 'Versiegelt' },
      verifyUrl: 'https://example.invalid/aufnahme/pruefen/abc123xyz'
    })
    const text = JSON.stringify(doc.content)
    expect(text).toContain('Mia')
    expect(text).toContain('Weiblich')
    expect(text).toContain('Ort, Datum, Unterschrift')
    expect(text).toContain('"qr":"https://example.invalid/aufnahme/pruefen/abc123xyz"')
  })

  it('puts the code and the QR link on the voucher card', () => {
    const doc = buildVoucherCardPdf({
      department: 'Mitte', formTitle: 'Aufnahmeantrag', code: '7KQ4-M2XR-9PDA',
      url: 'https://example.invalid/aufnahme#code=7KQ4-M2XR-9PDA', label: 'Ben', expiresAt: '2026-12-31T00:00:00Z'
    })
    const text = JSON.stringify(doc.content)
    expect(text).toContain('7KQ4-M2XR-9PDA')
    expect(text).toContain('"qr":"https://example.invalid/aufnahme#code=7KQ4-M2XR-9PDA"')
    expect(text).not.toContain('#code=7KQ4-M2XR-9PDA","fontSize":9')
  })
})
