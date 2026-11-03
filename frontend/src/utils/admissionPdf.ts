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
  applicantName?: string
  applicationNumber?: number
  /** SHA-256 of sealed files by answer key (attachments) */
  fileHashes?: Record<string, string>
  /** the recorded decision; without it the printout carries an empty decision box */
  decision?: {
    outcome: 'approved' | 'deferred' | 'rejected'
    decided_on: string
    body: string
    votes_yes: number | null
    votes_no: number | null
    votes_abstain: number | null
    recorded_by?: string
  }
}

export interface VoucherCardInput {
  department: string
  formTitle: string
  code: string
  url: string
  label: string
  expiresAt: string
}

const formatDate = (iso: string) =>
  new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })

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

// DIN A4 print design (canvas "Antrag A4"): Roboto, near-black on white, Feuerwehrrot accents.
const INK = '#111827'
const MUTED = '#4b5563'
const RULE = '#d1d5db'
const ACCENT = '#b91c1c'
const PAGE_WIDTH = 595.28
const MARGIN_X = 48
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

const WIDE_TYPES = new Set(['textarea'])
const CONSENT_PERSON = { applicant: 'Antragsteller*in', guardians: 'Erziehungsberechtigte' } as const

function box(checked: boolean): Content {
  return {
    width: 12,
    canvas: [
      { type: 'rect', x: 0, y: 1, w: 9, h: 9, lineWidth: 1, lineColor: INK },
      ...(checked
        ? [
            { type: 'line' as const, x1: 2, y1: 3, x2: 7, y2: 8, lineWidth: 1.2 },
            { type: 'line' as const, x1: 7, y1: 3, x2: 2, y2: 8, lineWidth: 1.2 }
          ]
        : [])
    ]
  } as Content
}

function hrule(color = RULE, width = 0.75): Content {
  return { canvas: [{ type: 'line', x1: 0, y1: 0, x2: CONTENT_WIDTH, y2: 0, lineWidth: width, lineColor: color }] }
}

function sectionTitle(number: number, title: string): Content {
  return {
    stack: [
      {
        text: [
          { text: `${number}  `, color: ACCENT },
          { text: title.toUpperCase(), color: INK }
        ],
        style: 'section'
      },
      hrule(INK, 0.75)
    ],
    margin: [0, 16, 0, 2],
    // Keep the heading on the page of its first rows.
    headlineLevel: 1
  }
}

const GAP = 18

/** Label above value over a hairline; ``width`` in pt, so the rule never pushes columns apart. */
function field(label: string, value: string, width: number): Content {
  return {
    width,
    stack: [
      { text: label, style: 'label' },
      { text: value || '–', style: 'value' },
      { canvas: [{ type: 'line', x1: 0, y1: 0, x2: width, y2: 0, lineWidth: 0.6, lineColor: RULE }], margin: [0, 4, 0, 0] }
    ],
    margin: [0, 5, 0, 0]
  } as Content
}

/** Fields in two columns within ``width``; wide ones take a whole row. */
function fieldGrid(items: { label: string; value: string; wide: boolean }[], width = CONTENT_WIDTH): Content[] {
  const half = (width - GAP) / 2
  const rows: Content[] = []
  let pending: { label: string; value: string } | null = null
  const flush = () => {
    if (!pending) return
    rows.push({ columns: [field(pending.label, pending.value, half)], columnGap: GAP })
    pending = null
  }
  for (const item of items) {
    if (item.wide) {
      flush()
      rows.push(field(item.label, item.value, width))
      continue
    }
    if (!pending) {
      pending = item
      continue
    }
    rows.push({ columns: [field(pending.label, pending.value, half), field(item.label, item.value, half)], columnGap: GAP })
    pending = null
  }
  flush()
  return rows
}

function answerName(value: unknown) {
  return value && typeof value === 'object' && 'name' in value ? String((value as { name: unknown }).name) : ''
}

function consentTable(rows: { element: FormElement; value: unknown }[]): Content {
  const header = ['Erklärung', 'Erteilt von', 'Antwort', 'Fassung'].map((text) => ({ text, style: 'th' }))
  return {
    table: {
      headerRows: 1,
      widths: ['*', 112, 46, 44],
      body: [
        header,
        ...rows.map(({ element, value }) => [
          { text: element.label ?? '' },
          {
            text:
              element.type === 'consent' ? CONSENT_PERSON[element.person ?? 'applicant'] : 'Antragsteller*in',
            color: MUTED
          },
          { columns: [box(value === true), { text: value === true ? 'ja' : 'nein' }], columnGap: 4 },
          { text: element.consent?.version ?? element.legal?.version ?? '–', color: MUTED, fontSize: 8 }
        ])
      ]
    },
    layout: tableLayout,
    margin: [0, 4, 0, 0]
  }
}

const tableLayout = {
  hLineWidth: (row: number) => (row === 1 ? 0.75 : 0.5),
  vLineWidth: () => 0,
  hLineColor: (row: number) => (row === 1 ? INK : RULE),
  paddingLeft: () => 4,
  paddingRight: () => 4,
  paddingTop: () => 5,
  paddingBottom: () => 5
}

function guardianBlock(element: FormElement, value: unknown): Content {
  const rows = Array.isArray(value) ? (value as Record<string, string>[]) : []
  const count = Math.max(rows.length, element.min ?? 1, 1)
  const others = (element.fields ?? []).filter((entry) => !['guardian.name', 'guardian.lastname'].includes(entry.target))
  return {
    stack: Array.from({ length: count }, (_, index) => {
      const row = rows[index] ?? {}
      const items = [
        { label: 'Name', value: [row.name, row.lastname].filter(Boolean).join(' '), wide: false },
        ...others.map((entry) => ({
          label: GUARDIAN_FIELD_META[entry.target]?.label ?? entry.target,
          value: row[entry.target.replace(/^guardian\./, '')] ?? '',
          wide: false
        }))
      ]
      return {
        stack: [{ text: `${index + 1}. Erziehungsberechtigte*r`, bold: true, fontSize: 9, margin: [0, 8, 0, 0] }, ...fieldGrid(items)],
        unbreakable: true
      }
    })
  }
}

function signatureCell(element: FormElement, image: string | undefined, place: string): Content {
  const label = element.label || SIGNATURE_ROLE_LABELS[element.role ?? 'applicant']
  return {
    stack: [
      image
        ? { image, fit: [200, 56], alignment: 'center', margin: [0, 0, 0, 2] }
        : { text: ' ', margin: [0, 0, 0, 44] },
      { canvas: [{ type: 'line', x1: 0, y1: 0, x2: 235, y2: 0, lineWidth: 1, lineColor: INK }] },
      {
        columns: [
          { text: label, bold: true, fontSize: 8, width: '*' },
          { text: image ? place : 'Ort, Datum', fontSize: 8, color: MUTED, alignment: 'right', width: 'auto' }
        ],
        margin: [0, 3, 0, 0]
      }
    ],
    unbreakable: true,
    margin: [0, 10, 0, 0]
  }
}

function signatureGrid(cells: Content[]): Content[] {
  const rows: Content[] = []
  for (let index = 0; index < cells.length; index += 2) {
    rows.push({ columns: [cells[index]!, cells[index + 1] ?? { text: '' }], columnGap: 24 })
  }
  return rows
}

function decisionBox(decision: ApplicationPdfInput['decision']): Content {
  const outcomes = ['aufgenommen', 'zurückgestellt', 'abgelehnt']
  const chosen = decision ? { approved: 0, deferred: 1, rejected: 2 }[decision.outcome] : -1
  const blank = (label: string, value = ''): Content => ({
    stack: [
      { text: value || ' ', fontSize: 9, margin: [0, 6, 0, 2] },
      { canvas: [{ type: 'line', x1: 0, y1: 0, x2: 140, y2: 0, lineWidth: 0.6, lineColor: MUTED }] },
      { text: label, style: 'label', margin: [0, 2, 0, 0] }
    ]
  })
  const votes = decision && decision.votes_yes !== null
    ? `${decision.votes_yes} / ${decision.votes_no ?? 0} / ${decision.votes_abstain ?? 0}`
    : ''
  return {
    table: {
      widths: ['*'],
      body: [
        [
          {
            stack: [
              {
                text: decision ? `BESCHLUSS · ${decision.body.toUpperCase()}` : 'BESCHLUSSVERMERK · VOM AUSSCHUSS AUSZUFÜLLEN',
                style: 'section'
              },
              {
                columns: outcomes.map((label, index) => ({
                  columns: [box(index === chosen), { text: label }],
                  columnGap: 4,
                  width: 'auto'
                })),
                columnGap: 22,
                margin: [0, 8, 0, 0]
              },
              {
                columns: [
                  blank('Sitzung vom', decision ? formatDate(decision.decided_on) : ''),
                  blank('Stimmen ja / nein / Enthaltung', votes),
                  blank(decision ? 'Erfasst von' : 'Unterschrift Vorsitz', decision?.recorded_by ?? '')
                ],
                columnGap: 16
              }
            ],
            margin: [8, 8, 8, 10]
          }
        ]
      ]
    },
    layout: { hLineWidth: () => 1.2, vLineWidth: () => 1.2, hLineColor: () => INK, vLineColor: () => INK },
    margin: [0, 18, 0, 0],
    unbreakable: true
  }
}

function sealStrip(input: ApplicationPdfInput, size: number, text: Content[]): Content {
  if (!input.seal) return ''
  return {
    table: {
      widths: [size + 8, '*'],
      body: [
        [
          input.verifyUrl ? { qr: input.verifyUrl, fit: size, margin: [2, 2, 2, 2] } : { text: '' },
          { stack: text, margin: [6, 2, 4, 2] }
        ]
      ]
    },
    layout: {
      hLineWidth: () => 0,
      vLineWidth: () => 0,
      fillColor: () => '#f3f4f6',
      paddingTop: () => 8,
      paddingBottom: () => 8
    }
  }
}

/** Content of one form page: fields in a grid, declarations as table, the rest in order. */
function pageContent(page: FormSchema['pages'][number], input: ApplicationPdfInput, age: number | null, place: string) {
  const out: Content[] = []
  for (const section of page.sections) {
    const visible = section.elements.filter((element) => isVisible(element.visible_if, input.answers, age))
    if (!visible.length) continue
    if (section.title && page.sections.length > 1) out.push({ text: section.title, style: 'subsection' })
    let fields: { label: string; value: string; wide: boolean }[] = []
    let declarations: { element: FormElement; value: unknown }[] = []
    let signatures: Content[] = []
    const photo = visible.find((element) => element.type === 'photo')
    const photoImage = photo?.key ? input.images[photo.key] : undefined
    const flush = () => {
      if (fields.length) {
        const withPhoto = !!photo && !out.some((entry) => (entry as { photo?: boolean }).photo)
        const grid = fieldGrid(fields, withPhoto ? CONTENT_WIDTH - 100 - GAP : CONTENT_WIDTH)
        out.push(
          withPhoto
            ? {
                columns: [
                  { width: '*', stack: grid },
                  {
                    width: 100,
                    stack: photoImage
                      ? [{ image: photoImage, fit: [100, 128] }, { text: 'Passbild', style: 'label', alignment: 'center' }]
                      : [
                          {
                            table: { widths: [92], heights: [118], body: [[{ text: 'Passbild\nnicht beigefügt', style: 'label', alignment: 'center', margin: [0, 48, 0, 0] }]] },
                            layout: { hLineColor: () => '#9ca3af', vLineColor: () => '#9ca3af' }
                          }
                        ],
                    margin: [0, 6, 0, 0]
                  }
                ],
                columnGap: 18,
                photo: true
              } as Content
            : { stack: grid }
        )
      }
      if (declarations.length) out.push(consentTable(declarations))
      if (signatures.length) out.push(...signatureGrid(signatures))
      fields = []
      declarations = []
      signatures = []
    }
    for (const element of visible) {
      const value = element.key ? input.answers[element.key] : undefined
      switch (element.type) {
        case 'photo':
          break
        case 'legal_ack':
        case 'consent':
          if (fields.length || signatures.length) flush()
          declarations.push({ element, value })
          break
        case 'signature':
          if (fields.length || declarations.length) flush()
          signatures.push(signatureCell(element, element.key ? input.images[element.key] : undefined, place))
          break
        case 'heading':
          flush()
          out.push({ text: element.label ?? '', style: 'subsection' })
          break
        case 'richtext':
          flush()
          out.push({ text: plain(element.html ?? ''), margin: [0, 4, 0, 4], lineHeight: 1.35 })
          break
        case 'divider':
          flush()
          out.push({ ...(hrule() as object), margin: [0, 6, 0, 6] } as Content)
          break
        case 'guardians':
          flush()
          out.push(guardianBlock(element, value))
          break
        case 'attachment':
          fields.push({ label: element.label ?? 'Anlage', value: answerName(value) || 'nicht beigefügt', wide: false })
          break
        case 'checkbox':
          if (!element.target) {
            flush()
            out.push({ columns: [box(value === true), { text: element.label ?? '' }], columnGap: 6, margin: [0, 6, 0, 0] })
            break
          }
          fields.push({ label: element.label ?? '', value: answerText(element, value), wide: false })
          break
        default:
          fields.push({ label: element.label ?? element.key ?? '', value: answerText(element, value), wide: WIDE_TYPES.has(element.type) })
      }
    }
    flush()
    // A photo without fields beside it stands on its own.
    if (photo && !out.some((entry) => (entry as { photo?: boolean }).photo)) {
      out.push({
        stack: photoImage
          ? [{ image: photoImage, fit: [100, 128] }, { text: 'Passbild', style: 'label' }]
          : [{ text: 'Passbild nicht beigefügt', style: 'label' }],
        margin: [0, 6, 0, 0],
        photo: true
      } as Content)
    }
  }
  return out
}

function attachmentTable(input: ApplicationPdfInput): Content[] {
  const rows = allElements(input.schema)
    .filter((element) => element.type === 'attachment' && element.key)
    .map((element) => ({ element, name: answerName(input.answers[element.key!]), hash: input.fileHashes?.[element.key!] ?? '' }))
    .filter((row) => row.name)
  if (!rows.length) return []
  return [
    {
      table: {
        headerRows: 1,
        widths: [150, '*', 110],
        body: [
          ['Anlage', 'Datei', 'Prüfsumme (SHA-256)'].map((text) => ({ text, style: 'th' })),
          ...rows.map((row) => [
            { text: row.element.label ?? 'Anlage' },
            { text: row.name },
            { text: row.hash ? `${row.hash.slice(0, 8)}…${row.hash.slice(-8)}` : '–', style: 'mono' }
          ])
        ]
      },
      layout: tableLayout,
      margin: [0, 4, 0, 0]
    },
    { text: 'Anlagen liegen digital vor; die Prüfsumme belegt, welche Datei eingereicht wurde.', style: 'note' }
  ]
}

export function buildApplicationPdf(input: ApplicationPdfInput): TDocumentDefinitions {
  const birthday = allElements(input.schema).find((element) => element.target === 'member.birthday')
  const birthdayValue = birthday?.key ? input.answers[birthday.key] : null
  const age = ageOn(typeof birthdayValue === 'string' ? birthdayValue : null)
  const place = input.submittedAt ? formatDate(input.submittedAt) : ''
  const applicant = input.applicantName || 'Aufnahmeantrag'
  const reference = input.seal ? `Siegel ${input.seal.publicId}` : ''

  const body: Content[] = []
  let number = 0
  for (const page of input.schema.pages) {
    const content = pageContent(page, input, age, place)
    if (!content.length) continue
    body.push(sectionTitle(++number, page.title))
    body.push(...content)
  }
  const attachments = attachmentTable(input)
  if (attachments.length) body.push(sectionTitle(++number, 'Anlagen'), ...attachments)

  const received: Content = input.submittedAt
    ? ({
        width: 150,
        table: {
          widths: ['*', 'auto'],
          body: [
            [{ text: 'Eingegangen', color: MUTED }, { text: formatDate(input.submittedAt), bold: true }],
            [{ text: 'Uhrzeit', color: MUTED }, { text: new Date(input.submittedAt).toLocaleTimeString('de-DE', { timeStyle: 'short' }), bold: true }],
            ...(input.applicationNumber ? [[{ text: 'Antrag Nr.', color: MUTED }, { text: String(input.applicationNumber), bold: true }]] : [])
          ]
        },
        layout: {
          hLineWidth: (row: number, node: { table: { body: unknown[] } }) =>
            row === 0 || row === node.table.body.length ? 0.75 : 0,
          vLineWidth: (column: number) => (column === 0 || column === 2 ? 0.75 : 0),
          paddingLeft: () => 8,
          paddingRight: () => 8,
          paddingTop: () => 4,
          paddingBottom: () => 4
        },
        fontSize: 9
      } as Content)
    : ({ width: 150, text: '' } as Content)

  return {
    pageSize: 'A4',
    pageMargins: [MARGIN_X, 56, MARGIN_X, 48],
    info: { title: `${input.title} · ${applicant}` },
    content: [
      {
        columns: [
          {
            width: '*',
            stack: [
              { text: input.department.toUpperCase(), color: ACCENT, bold: true, fontSize: 8, characterSpacing: 1 },
              { text: input.title, fontSize: 24, bold: true, margin: [0, 4, 0, 2] },
              { text: input.applicantName ? `für ${input.applicantName}` : '', fontSize: 10, color: MUTED }
            ]
          },
          received
        ],
        columnGap: 18
      },
      { canvas: [{ type: 'rect', x: 0, y: 0, w: CONTENT_WIDTH, h: 2.2, color: ACCENT }], margin: [0, 14, 0, 12] },
      sealStrip(input, 56, [
        { text: input.seal?.label ?? '', bold: true, fontSize: 9.5 },
        { text: [{ text: 'Siegel-ID ', color: MUTED }, { text: input.seal?.publicId ?? '', bold: true, characterSpacing: 0.5 }], fontSize: 9 },
        { text: `Prüfsumme ${input.seal?.sealHash ?? ''}`, style: 'mono' },
        { text: 'Echtheit prüfen: QR-Code scannen oder die Siegel-ID auf der Prüfseite eingeben.', style: 'note' }
      ]),
      ...body,
      decisionBox(input.decision),
      input.seal
        ? {
            ...(sealStrip(input, 44, [
              {
                text: 'Dieser Ausdruck gibt den versiegelten Antrag wieder. Nachträgliche Änderungen sind ausgeschlossen; ob der Inhalt unverändert ist, zeigt die Prüfseite zur Siegel-ID.',
                fontSize: 8.5,
                lineHeight: 1.3
              }
            ]) as object),
            margin: [0, 14, 0, 0],
            unbreakable: true
          } as Content
        : ''
    ],
    header: (current: number) =>
      current === 1
        ? ''
        : {
            margin: [MARGIN_X, 24, MARGIN_X, 0],
            stack: [
              {
                columns: [
                  { text: `${input.title} · ${applicant}`, bold: true, fontSize: 9.5 },
                  { text: input.department, alignment: 'right', fontSize: 8.5, color: MUTED }
                ]
              },
              { canvas: [{ type: 'rect', x: 0, y: 0, w: CONTENT_WIDTH, h: 1.6, color: ACCENT }], margin: [0, 5, 0, 0] }
            ]
          },
    footer: (current: number, total: number) => ({
      margin: [MARGIN_X, 14, MARGIN_X, 0],
      stack: [
        hrule(),
        {
          columns: [
            { text: [input.title, applicant !== input.title ? applicant : '', reference].filter(Boolean).join(' · ') },
            { text: `Seite ${current} von ${total}`, alignment: 'right' }
          ],
          fontSize: 8,
          color: MUTED,
          margin: [0, 5, 0, 0]
        }
      ]
    }),
    pageBreakBefore: (node) => {
      // A section title never sits alone at the bottom of a page.
      const current = node as unknown as { headlineLevel?: number; startPosition: { top: number; pageInnerHeight: number } }
      return current.headlineLevel === 1 && current.startPosition.top > current.startPosition.pageInnerHeight - 90
    },
    styles: {
      section: { fontSize: 9.5, bold: true, characterSpacing: 0.8, margin: [0, 0, 0, 4] },
      subsection: { fontSize: 9.5, bold: true, margin: [0, 10, 0, 0] },
      label: { fontSize: 7.5, color: MUTED },
      value: { fontSize: 10, color: INK, margin: [0, 2, 0, 0] },
      th: { fontSize: 7.5, color: MUTED },
      note: { fontSize: 7.5, color: MUTED, margin: [0, 3, 0, 0] },
      mono: { fontSize: 7, color: MUTED }
    },
    defaultStyle: { font: 'Roboto', fontSize: 9.5, color: INK, lineHeight: 1.2 }
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
