/**
 * Printouts of the admissions module as pdfmake documents: the filled-in application (with seal
 * and verification QR) and the voucher card handed to a prospective member.
 * Pure: images arrive as data URLs, the caller loads pdfmake.
 */
import type { Content, TDocumentDefinitions } from 'pdfmake/interfaces'
import type { FormElement, FormSchema, SignatureMode } from '@/types/admissions'
import { GENDER_OPTIONS, GUARDIAN_FIELD_META, SIGNATURE_ROLE_LABELS, ageOn, allElements, isVisible } from './admissionSchema'

export interface ApplicationPdfInput {
  title: string
  department: string
  schema: FormSchema
  answers: Record<string, unknown>
  /** data URLs by answer key (photo, signatures) */
  images: Record<string, string>
  signatureMode: SignatureMode
  submittedAt?: string
  seal?: { publicId: string; sealHash: string; label: string }
  verifyUrl?: string
}

export interface VoucherCardInput {
  department: string
  formTitle: string
  code: string
  url: string
  label: string
  expiresAt: string
}

const formatDate = (iso: string) => new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString('de-DE')
const formatDateTime = (iso: string) => new Date(iso).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' })

function plain(html: string) {
  return html
    .replace(/<\/(p|li|h\d)>/gi, '\n')
    .replace(/<li>/gi, '• ')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function answerText(element: FormElement, value: unknown): string {
  if (value === undefined || value === null || value === '') return '–'
  if (element.type === 'checkbox') return value === true ? 'Ja' : 'Nein'
  if (element.type === 'date' && typeof value === 'string') return formatDate(value)
  if (element.type === 'select' || element.type === 'radio') {
    const options = element.target === 'member.gender' ? GENDER_OPTIONS : (element.options ?? [])
    return options.find((option) => option.value === value)?.label ?? String(value)
  }
  return String(value)
}

function checkbox(checked: boolean, text: string, note = ''): Content {
  return {
    columns: [
      {
        width: 14,
        canvas: [
          { type: 'rect', x: 0, y: 1, w: 8, h: 8, lineWidth: 0.7 },
          ...(checked
            ? [
                { type: 'line' as const, x1: 1.5, y1: 5, x2: 3.5, y2: 7.5, lineWidth: 1.1 },
                { type: 'line' as const, x1: 3.5, y1: 7.5, x2: 7, y2: 2, lineWidth: 1.1 }
              ]
            : [])
        ]
      },
      { width: '*', stack: [{ text }, ...(note ? [{ text: note, style: 'muted' }] : [])] }
    ],
    margin: [0, 2, 0, 2]
  }
}

function signatureBlock(element: FormElement, image: string | undefined, mode: SignatureMode): Content {
  const label = element.label || SIGNATURE_ROLE_LABELS[element.role ?? 'applicant']
  const parts: Content[] = []
  if (image) parts.push({ image, fit: [220, 70], margin: [0, 4, 0, 0] })
  if (mode !== 'digital') {
    parts.push({
      canvas: [{ type: 'line', x1: 0, y1: 0, x2: 230, y2: 0, lineWidth: 0.6, dash: { length: 2 } }],
      margin: [0, image ? 6 : 34, 0, 2]
    })
    parts.push({ text: `Ort, Datum, Unterschrift ${label}`, style: 'muted' })
  } else {
    parts.push({ text: label, style: 'muted' })
  }
  return { stack: parts, margin: [0, 6, 0, 6], unbreakable: true }
}

function elementContent(element: FormElement, input: ApplicationPdfInput): Content | null {
  const value = element.key ? input.answers[element.key] : undefined
  switch (element.type) {
    case 'heading':
      return { text: element.label ?? '', style: 'h3' }
    case 'richtext':
      return { text: plain(element.html ?? ''), margin: [0, 2, 0, 4] }
    case 'divider':
      return { canvas: [{ type: 'line', x1: 0, y1: 0, x2: 515, y2: 0, lineWidth: 0.4 }], margin: [0, 4, 0, 4] }
    case 'legal_ack':
      return checkbox(value === true, element.label ?? '', element.legal ? `${element.legal.title} (${element.legal.version})` : '')
    case 'consent':
      return checkbox(
        value === true,
        element.label ?? '',
        [element.consent?.text, element.person === 'guardians' ? 'Erklärung der Sorgeberechtigten' : ''].filter(Boolean).join(' · ')
      )
    case 'checkbox':
      return checkbox(value === true, element.label ?? '')
    case 'photo': {
      const image = element.key ? input.images[element.key] : undefined
      return image
        ? { stack: [{ text: element.label ?? 'Passbild', style: 'label' }, { image, fit: [90, 120] }], margin: [0, 4, 0, 4] }
        : { columns: [{ width: 170, text: element.label ?? 'Passbild', style: 'label' }, { text: 'nicht beigefügt' }] }
    }
    case 'signature':
      return signatureBlock(element, element.key ? input.images[element.key] : undefined, input.signatureMode)
    case 'guardians': {
      const rows = Array.isArray(value) ? (value as Record<string, string>[]) : []
      if (!rows.length) return null
      const fields = element.fields ?? []
      return {
        stack: rows.map((row, index) => ({
          stack: [
            { text: `${index + 1}. Erziehungsberechtigte*r`, style: 'label', margin: [0, 4, 0, 2] },
            ...fields.map((field) => ({
              columns: [
                { width: 170, text: GUARDIAN_FIELD_META[field.target]?.label ?? field.target, style: 'muted' },
                { text: row[field.target.replace(/^guardian\./, '')] || '–' }
              ]
            }))
          ]
        }))
      }
    }
    default:
      return {
        columns: [
          { width: 170, text: element.label ?? element.key ?? '', style: 'muted' },
          { text: answerText(element, value) }
        ],
        margin: [0, 1, 0, 1]
      }
  }
}

export function buildApplicationPdf(input: ApplicationPdfInput): TDocumentDefinitions {
  const birthday = allElements(input.schema).find((element) => element.target === 'member.birthday')
  const birthdayValue = birthday?.key ? input.answers[birthday.key] : null
  const age = ageOn(typeof birthdayValue === 'string' ? birthdayValue : null)
  const body: Content[] = []
  for (const page of input.schema.pages) {
    body.push({ text: page.title, style: 'h2' })
    for (const section of page.sections) {
      if (section.title) body.push({ text: section.title, style: 'h3' })
      for (const element of section.elements) {
        if (!isVisible(element.visible_if, input.answers, age)) continue
        const content = elementContent(element, input)
        if (content) body.push(content)
      }
    }
  }

  const sealBox: Content[] = input.seal
    ? [
        {
          margin: [0, 16, 0, 0],
          table: {
            widths: ['*', 90],
            body: [
              [
                {
                  stack: [
                    { text: input.seal.label, bold: true },
                    { text: `Siegel-ID: ${input.seal.publicId}` },
                    { text: `Prüfsumme: ${input.seal.sealHash}`, style: 'mono' },
                    input.verifyUrl ? { text: `Prüfen: ${input.verifyUrl}`, style: 'muted' } : ''
                  ]
                },
                input.verifyUrl ? { qr: input.verifyUrl, fit: 86, alignment: 'right' } : ''
              ]
            ]
          },
          layout: 'lightHorizontalLines'
        }
      ]
    : []

  return {
    pageSize: 'A4',
    pageMargins: [40, 50, 40, 50],
    info: { title: input.title },
    content: [
      { text: input.title, style: 'h1' },
      {
        text: [input.department, input.submittedAt ? `eingereicht am ${formatDateTime(input.submittedAt)}` : '']
          .filter(Boolean)
          .join(' · '),
        style: 'muted',
        margin: [0, 0, 0, 10]
      },
      ...body,
      ...sealBox
    ],
    footer: (current: number, total: number) => ({
      text: `${input.title} · Seite ${current} von ${total}`,
      style: 'muted',
      alignment: 'center',
      margin: [0, 20, 0, 0]
    }),
    styles: {
      h1: { fontSize: 18, bold: true, margin: [0, 0, 0, 2] },
      h2: { fontSize: 13, bold: true, margin: [0, 12, 0, 4] },
      h3: { fontSize: 10, bold: true, color: '#555555', margin: [0, 8, 0, 2] },
      label: { bold: true },
      muted: { fontSize: 8, color: '#666666' },
      mono: { fontSize: 7, color: '#444444' }
    },
    defaultStyle: { fontSize: 9.5, lineHeight: 1.2 }
  }
}

export function buildVoucherCardPdf(input: VoucherCardInput): TDocumentDefinitions {
  return {
    pageSize: 'A6',
    pageOrientation: 'landscape',
    pageMargins: [24, 22, 24, 22],
    info: { title: `Aufnahme-Code ${input.label}` },
    content: [
      {
        columns: [
          {
            width: '*',
            stack: [
              { text: input.department, fontSize: 9, color: '#666666' },
              { text: input.formTitle, fontSize: 15, bold: true, margin: [0, 2, 0, 8] },
              input.label ? { text: `Für: ${input.label}`, margin: [0, 0, 0, 6] } : '',
              { text: 'QR-Code scannen oder Code eingeben unter', fontSize: 8, color: '#666666' },
              { text: input.url.split('#')[0] ?? input.url, fontSize: 9, margin: [0, 0, 0, 6] },
              { text: input.code, fontSize: 18, bold: true, characterSpacing: 1.5 },
              { text: `Gültig bis ${formatDate(input.expiresAt)} · nur einmal verwendbar`, fontSize: 8, color: '#666666', margin: [0, 6, 0, 0] }
            ]
          },
          { width: 130, qr: input.url, fit: 130, alignment: 'right' }
        ]
      }
    ],
    defaultStyle: { fontSize: 10 }
  }
}

/** Load pdfmake with its fonts and download a document. */
export async function downloadPdf(definition: TDocumentDefinitions, filename: string) {
  const [{ default: pdfMake }, { default: pdfFonts }] = await Promise.all([
    import('pdfmake/build/pdfmake'),
    import('pdfmake/build/vfs_fonts')
  ])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- pdfmake's runtime API is untyped
  const pdf = pdfMake as any
  pdf.addVirtualFileSystem(pdfFonts)
  await pdf.createPdf(definition).download(filename)
}

/** Fetch a private image (session cookie) as a data URL for the PDF. */
export async function imageAsDataUrl(url: string): Promise<string> {
  const response = await fetch(url, { credentials: 'same-origin' })
  if (!response.ok) throw new Error('Bild nicht verfügbar')
  const blob = await response.blob()
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}
