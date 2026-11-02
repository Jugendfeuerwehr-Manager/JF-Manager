/**
 * Trainer handout as a pdfmake document. The handout is a working paper for
 * the training itself: page 1 shows the whole plan, then who is where, then one
 * sheet per station to hand to its instructors, then the packing list.
 *
 * Pure apart from `renderHtml`, which the caller supplies (block content is
 * HTML and needs the browser's parser and private media access).
 */
import type { Content, ContentStack, TDocumentDefinitions } from 'pdfmake/interfaces'
import type { BlockKind, TrainingBlock, TrainingSessionHandout } from '@/types/training'
import { resolveBrand } from '@/theme/brand'
import { mixHex, safeBlockColor } from './blockColor'
import {
  blockEnd, blockLaneRuns, byStart, clockTime, handoutLanes, instructorAssignments, laneBlocks, materialSummary,
  stationCards, timeSpan, type HandoutLane, type StationCard,
} from './handoutSummary'

/** PNG/JPEG data URL or SVG markup. */
export type HandoutLogo = { image: string } | { svg: string }

/**
 * Everything an organisation may brand. Kept in one object so later
 * user-defined layouts only have to fill it in.
 */
export interface HandoutTheme {
  /** Base colour (#rrggbb) as chosen in the settings; print shades are derived from it. */
  brandColor: string
  orgName: string
  logo: HandoutLogo | null
}

export interface HandoutPdfOptions {
  theme?: Partial<HandoutTheme>
  renderHtml?: (html: string) => Promise<Content[]>
}

// A4 portrait in pt
const PAGE_WIDTH = 595.28
const PAGE_HEIGHT = 841.89
const MARGIN_X = 40
const MARGIN_TOP = 54
const MARGIN_BOTTOM = 40
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

const INK = '#1e293b'
const MUTED = '#64748b'
const LINE = '#e2e8f0'
const WARN = '#b45309'

const STATUS_LABELS: Record<TrainingSessionHandout['status'], string> = {
  draft: 'Entwurf', published: 'Veröffentlicht', completed: 'Abgeschlossen', cancelled: 'Abgesagt',
}

const NEUTRAL_KINDS: Partial<Record<BlockKind, string>> = { break: '#94a3b8', transition: '#cbd5e1' }

interface Palette {
  /** Readable on white; the shade the app uses for buttons and links */
  brand: string
  soft: string
}

/** Same derivation as the app (DES-01.6), so print matches the chosen colour scheme. */
function palette(base: string): Palette {
  const roles = resolveBrand(base)
  return { brand: roles.light.color, soft: roles.scale[200] }
}

function formatDuration(minutes: number) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h ? `${h}:${String(m).padStart(2, '0')} h` : `${m} Min.`
}

function blockColor(block: TrainingBlock, brand: string) {
  return safeBlockColor(block.color) ?? NEUTRAL_KINDS[block.kind ?? 'block'] ?? brand
}

function logoNode(logo: HandoutLogo, size: number): Record<string, unknown> {
  return 'svg' in logo ? { svg: logo.svg, fit: [size, size] } : { image: 'logo', fit: [size * 2.5, size] }
}

// ── Swimlane overview (SVG) ──────────────────────────────────────────────────

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

// Roboto averages; good enough to wrap and truncate inside the boxes.
const textWidth = (s: string, size: number, bold = false) => s.length * size * (bold ? 0.56 : 0.52)

function wrap(text: string, width: number, size: number, maxLines: number, bold = false): string[] {
  if (maxLines < 1) return []
  const lines: string[] = []
  let current = ''
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = current ? `${current} ${word}` : word
    if (textWidth(next, size, bold) <= width || !current) current = next
    else {
      lines.push(current)
      current = word
    }
  }
  if (current) lines.push(current)
  const kept = lines.slice(0, maxLines)
  const lastIndex = kept.length - 1
  let last = kept[lastIndex] ?? ''
  if (lines.length > maxLines || textWidth(last, size, bold) > width) {
    while (last.length > 1 && textWidth(`${last}…`, size, bold) > width) last = last.slice(0, -1)
    kept[lastIndex] = `${last.trimEnd()}…`
  }
  return kept
}

function swimlaneSvg(h: TrainingSessionHandout, lanes: HandoutLane[], p: Palette, maxHeight: number) {
  const total = Math.max(30, ...h.blocks.map(blockEnd))
  const axisW = 32
  const headerH = 18
  const laneW = (CONTENT_WIDTH - axisW) / lanes.length
  const ppm = Math.min(4, Math.max(1.2, (maxHeight - headerH - 8) / total))
  const bodyH = total * ppm
  const height = headerH + bodyH + 6
  const y0 = headerH
  const out: string[] = []

  lanes.forEach((lane, i) => {
    const x = axisW + i * laneW
    const name = wrap(lane.label, laneW - 8, 8, 1, true)[0] ?? ''
    out.push(`<text x="${x + 4}" y="${headerH - 6}" font-family="Roboto" font-weight="bold" font-size="8" fill="${INK}">${esc(name)}</text>`)
    if (i > 0) out.push(`<line x1="${x}" y1="${y0}" x2="${x}" y2="${y0 + bodyH}" stroke="${LINE}" stroke-width="0.5"/>`)
  })
  out.push(`<line x1="${axisW}" y1="${y0 - 0.75}" x2="${CONTENT_WIDTH}" y2="${y0 - 0.75}" stroke="${p.brand}" stroke-width="1.5"/>`)

  const step = ppm * 15 >= 16 ? 15 : ppm * 30 >= 16 ? 30 : 60
  for (let t = 0; t <= total; t += step) {
    const y = y0 + t * ppm
    const full = (h.start_time ? Number(h.start_time.split(':')[1] ?? 0) + t : t) % 60 === 0
    if (t > 0) out.push(`<line x1="${axisW}" y1="${y}" x2="${CONTENT_WIDTH}" y2="${y}" stroke="${LINE}" stroke-width="0.4"${full ? '' : ' stroke-dasharray="1.5,2"'}/>`)
    out.push(`<text x="${axisW - 5}" y="${y + (t === 0 ? 7 : 2.5)}" text-anchor="end" font-family="Roboto" font-size="6.5" ${full ? 'font-weight="bold" ' : ''}fill="${full ? INK : MUTED}">${clockTime(t, h.start_time)}</text>`)
  }

  for (const block of [...h.blocks].sort(byStart)) {
    const color = blockColor(block, p.brand)
    const y = y0 + block.start_offset_minutes * ppm + 1
    const bh = Math.max(3, block.duration_minutes * ppm - 2)
    for (const [from, to] of blockLaneRuns(block, lanes)) {
      const x = axisW + from * laneW + 2
      const w = (to - from + 1) * laneW - 4
      out.push(`<rect x="${x}" y="${y}" width="${w}" height="${bh}" rx="2" fill="${mixHex(color, '#ffffff', 10)}"/>`)
      out.push(`<rect x="${x}" y="${y}" width="2.5" height="${bh}" fill="${color}"/>`)
      out.push(...boxText(block, h, x + 6, y, w - 9, bh))
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${CONTENT_WIDTH}" height="${height}" viewBox="0 0 ${CONTENT_WIDTH} ${height}">${out.join('')}</svg>`
}

function boxText(block: TrainingBlock, h: TrainingSessionHandout, x: number, y: number, w: number, bh: number): string[] {
  if (bh < 8) return []
  const titleSize = bh < 12 ? 6.5 : 7.5
  const small = 6.5
  const room = bh - 3
  const time = timeSpan(block.start_offset_minutes, blockEnd(block), h.start_time)
  const inlineTime = room < 22
  const titleLines = Math.max(1, Math.min(2, Math.floor((room - (inlineTime ? 0 : small + 2)) / (titleSize + 2))))
  const lines: Array<{ text: string; size: number; bold: boolean; color: string }> = []
  for (const line of wrap(block.title, inlineTime ? w - textWidth(time, small) - 6 : w, titleSize, titleLines, true)) {
    lines.push({ text: line, size: titleSize, bold: true, color: INK })
  }
  const details = [
    inlineTime ? '' : [time, block.location].filter(Boolean).join(' · '),
    block.instructors?.length ? block.instructors.map((i) => i.name).join(', ') : '',
  ].filter(Boolean)
  for (const detail of details) lines.push({ text: detail, size: small, bold: false, color: MUTED })

  const out: string[] = []
  let used = 0
  for (const line of lines) {
    const lh = line.size + 2
    if (used + lh > room) break
    const text = line.bold ? line.text : wrap(line.text, w, line.size, 1)[0] ?? ''
    out.push(`<text x="${x}" y="${y + 2 + used + line.size}" font-family="Roboto" font-size="${line.size}"${line.bold ? ' font-weight="bold"' : ''} fill="${line.color}">${esc(text)}</text>`)
    used += lh
  }
  if (inlineTime && w > textWidth(time, small) + 30) {
    out.push(`<text x="${x + w}" y="${y + 2 + titleSize}" text-anchor="end" font-family="Roboto" font-size="${small}" fill="${MUTED}">${time}</text>`)
  }
  return out
}

// ── Building blocks ──────────────────────────────────────────────────────────

function checkbox(size = 8.5): Content {
  return { canvas: [{ type: 'rect', x: 0, y: 0, w: size, h: size, r: 1.5, lineWidth: 0.7, lineColor: '#94a3b8' }], margin: [0, 1, 0, 0] }
}

function sectionTitle(text: string, p: Palette): ContentStack {
  return {
    stack: [
      { text, fontSize: 12, bold: true, color: INK },
      { canvas: [{ type: 'line', x1: 0, y1: 0, x2: 20, y2: 0, lineWidth: 1.5, lineColor: p.brand }], margin: [0, 3, 0, 0] },
    ],
    margin: [0, 0, 0, 8],
  }
}

function subTitle(text: string): Content {
  return { text, fontSize: 9.5, bold: true, color: INK, margin: [0, 6, 0, 4] }
}

function tableLayout(p: Palette) {
  return {
    hLineWidth: (i: number) => (i === 0 ? 0 : i === 1 ? 0.8 : 0.4),
    vLineWidth: () => 0,
    hLineColor: (i: number) => (i === 1 ? p.soft : LINE),
    paddingLeft: (i: number) => (i === 0 ? 0 : 5),
    paddingRight: () => 5,
    paddingTop: () => 3.5,
    paddingBottom: () => 3.5,
  }
}

function th(text: string) {
  return { text: text.toUpperCase(), fontSize: 6.5, bold: true, color: MUTED, characterSpacing: 0.6 }
}

function label(text: string): Content {
  return { text: text.toUpperCase(), fontSize: 6.5, bold: true, color: MUTED, characterSpacing: 0.6, margin: [0, 0, 0, 1] }
}

/** Lined area for handwritten notes during the training. */
function noteLines(count: number): Content {
  return {
    canvas: Array.from({ length: count }, (_, i) => ({
      type: 'line' as const, x1: 0, y1: i * 18 + 16, x2: CONTENT_WIDTH, y2: i * 18 + 16, lineWidth: 0.4, lineColor: '#cbd5e1',
    })),
  }
}

function note(title: string, text: string, color: string): Content {
  return {
    table: {
      widths: [1.5, '*'],
      body: [[
        { text: '', fillColor: color },
        { stack: [{ text: title, fontSize: 7.5, bold: true, color, margin: [0, 0, 0, 1] }, { text, fontSize: 9, lineHeight: 1.3 }], margin: [7, 1, 0, 1] },
      ]],
    },
    layout: 'noBorders',
    margin: [0, 0, 0, 8],
  } as Content
}

// ── Pages ────────────────────────────────────────────────────────────────────

function hero(h: TrainingSessionHandout, theme: HandoutTheme, p: Palette): Content[] {
  const date = new Date(h.date).toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  const time = h.start_time ? `${h.start_time.slice(0, 5)}${h.end_time ? `–${h.end_time.slice(0, 5)}` : ''} Uhr` : ''
  return [
    {
      columns: [
        ...(theme.logo ? [{ ...logoNode(theme.logo, 40), width: 'auto', margin: [0, 2, 12, 0] }] : []),
        {
          stack: [
            { text: [theme.orgName, `Ausbildungsplan · ${STATUS_LABELS[h.status]}`].filter(Boolean).join('  ·  '), fontSize: 8, bold: true, color: p.brand },
            { text: h.title, fontSize: 19, bold: true, color: INK, margin: [0, 2, 0, 2] },
            { text: [date, time, h.location].filter(Boolean).join('  ·  '), fontSize: 9, color: MUTED },
          ],
        },
      ],
      margin: [0, 0, 0, 10],
    } as Content,
    { canvas: [{ type: 'line', x1: 0, y1: 0, x2: CONTENT_WIDTH, y2: 0, lineWidth: 0.6, lineColor: LINE }], margin: [0, 0, 0, 8] },
  ]
}

function facts(h: TrainingSessionHandout, lanes: HandoutLane[], cards: StationCard[]): Content {
  const total = h.blocks.length ? Math.max(...h.blocks.map(blockEnd)) : 0
  const instructors = new Set(h.blocks.flatMap((b) => (b.instructors ?? []).map((i) => i.id)))
  const open = cards.filter((c) => !c.instructors.length).length
  const groups = lanes[0]?.groupId === null ? 0 : lanes.length
  const items: Array<[string, string]> = [
    ['Dauer', formatDuration(total)],
    ...(groups ? [['Gruppen', String(groups)] as [string, string]] : []),
    ['Stationen', String(cards.length)],
    ['Ausbilder', String(instructors.size)],
  ]
  return {
    text: [
      ...items.flatMap(([name, value], i) => [
        { text: i ? '     ' : '' },
        { text: `${name} `, color: MUTED },
        { text: value, bold: true },
      ]),
      ...(open ? [{ text: `     ${open} Station${open === 1 ? '' : 'en'} unbesetzt`, bold: true, color: WARN }] : []),
    ],
    fontSize: 8.5,
    margin: [0, 0, 0, 14],
  } as Content
}

function assignmentTable(h: TrainingSessionHandout, p: Palette): Content[] {
  const assignments = instructorAssignments(h.blocks)
  if (!assignments.length) return []
  const rows: unknown[][] = [[th('Ausbilder'), th('Einsatz'), th('Ort'), th('Zeit')]]
  for (const person of assignments) {
    person.duties.forEach((duty, i) => {
      rows.push([
        i === 0 ? { text: person.name, bold: true, color: person.id === null ? WARN : INK, rowSpan: person.duties.length } : '',
        duty.title,
        { text: duty.location || '—', color: duty.location ? INK : MUTED },
        { text: duty.slots.map(([s, e]) => timeSpan(s, e, h.start_time)).join('\n'), color: MUTED, fontSize: 8 },
      ])
    })
  }
  return [
    sectionTitle('Wer ist wo?', p),
    { table: { headerRows: 1, dontBreakRows: true, widths: [100, '*', 100, 64], body: rows }, layout: tableLayout(p), fontSize: 8.5, margin: [0, 0, 0, 16] } as Content,
  ]
}

function routeTables(h: TrainingSessionHandout, lanes: HandoutLane[], p: Palette): Content[] {
  const out: Content[] = []
  // The section title travels with the first table so it never ends a page alone.
  let title: Content[] = [sectionTitle(lanes.length > 1 ? 'Laufzettel der Gruppen' : 'Übungsablauf', p)]
  for (const lane of lanes) {
    const blocks = laneBlocks(h.blocks, lane)
    if (!blocks.length) continue
    const rows: unknown[][] = [[th('Zeit'), th('Programmpunkt'), th('Ort'), th('Ausbilder')]]
    for (const b of blocks) {
      rows.push([
        { text: timeSpan(b.start_offset_minutes, blockEnd(b), h.start_time), bold: true, noWrap: true },
        {
          columns: [
            { canvas: [{ type: 'rect', x: 0, y: 2, w: 5, h: 5, r: 1, color: blockColor(b, p.brand) }], width: 9 },
            { text: b.title },
          ],
        },
        { text: b.location || '', color: MUTED },
        { text: (b.instructors ?? []).map((i) => i.name).join(', '), color: MUTED },
      ])
    }
    out.push({
      unbreakable: blocks.length < 18,
      stack: [
        ...title,
        ...(lanes.length > 1 ? [subTitle(lane.label)] : []),
        { table: { headerRows: 1, dontBreakRows: true, widths: [58, '*', 100, 100], body: rows }, layout: tableLayout(p), fontSize: 8.5 },
      ],
      margin: [0, 0, 0, 10],
    } as Content)
    title = []
  }
  return out
}

async function stationSheet(
  card: StationCard, index: number, count: number, block: TrainingBlock | undefined,
  h: TrainingSessionHandout, p: Palette, renderHtml: HandoutPdfOptions['renderHtml'],
): Promise<Content[]> {
  const color = block ? blockColor(block, p.brand) : p.brand
  const duration = card.slots[0] ? card.slots[0].end - card.slots[0].start : 0
  const out: Content[] = [
    {
      columns: [
        {
          stack: [
            { text: `STATION ${index + 1} VON ${count}`, fontSize: 7, bold: true, characterSpacing: 1, color: p.brand },
            { text: card.title, fontSize: 18, bold: true, color: INK, margin: [0, 1, 0, 0] },
          ],
        },
        { text: [{ text: `${duration}`, fontSize: 14, bold: true, color: INK }, { text: ' Min. je Durchgang', fontSize: 8, color: MUTED }], width: 'auto', margin: [0, 10, 0, 0] },
      ],
      pageBreak: 'before',
    } as Content,
    { canvas: [{ type: 'line', x1: 0, y1: 0, x2: CONTENT_WIDTH, y2: 0, lineWidth: 1.5, lineColor: color }], margin: [0, 6, 0, 10] },
    {
      columns: [
        { stack: [label('Ort'), { text: card.location || '—', fontSize: 10, bold: true }] },
        {
          stack: [
            label('Ausbilder'),
            card.instructors.length
              ? { text: card.instructors.map((i) => i.name).join(', '), fontSize: 10, bold: true }
              : { text: 'noch nicht besetzt', fontSize: 10, bold: true, color: WARN },
          ],
        },
      ],
      columnGap: 16,
      margin: [0, 0, 0, 10],
    } as Content,
    subTitle('Durchgänge'),
    {
      table: {
        headerRows: 1,
        widths: [64, '*', 80, 12],
        body: [
          [th('Zeit'), th('Gruppe'), th('Anwesend'), ''],
          ...card.slots.map((slot) => [
            { text: timeSpan(slot.start, slot.end, h.start_time), bold: true },
            slot.groups,
            '',
            checkbox(),
          ]),
        ],
      },
      layout: tableLayout(p),
      fontSize: 9,
      margin: [0, 0, 0, 10],
    } as Content,
  ]

  if (card.learningObjective) out.push(note('Lernziel', card.learningObjective, p.brand))
  if (card.safetyNotes) out.push(note('Sicherheit', card.safetyNotes, WARN))

  if (card.materials.length) {
    out.push(subTitle('Material'))
    out.push({
      table: {
        widths: [9, 'auto', '*'],
        body: card.materials.map((m) => [checkbox(), { text: `${m.quantity} ×`, bold: true, alignment: 'right' }, m.label]),
      },
      layout: { hLineWidth: () => 0, vLineWidth: () => 0, paddingLeft: (i: number) => (i === 0 ? 0 : 4), paddingRight: () => 2, paddingTop: () => 1.5, paddingBottom: () => 1.5 },
      fontSize: 9,
      margin: [0, 0, 0, 8],
    } as Content)
  }

  if (block?.content && renderHtml) {
    const body = await renderHtml(block.content)
    if (body.length) out.push(subTitle('Ablauf'), ...body)
  }
  out.push(...attachmentList(block))
  out.push(subTitle('Notizen'), noteLines(5))
  return out
}

function attachmentList(block: TrainingBlock | undefined): Content[] {
  const docs = (block?.attachments ?? []).filter((a) => a.file_url)
  if (!docs.length) return []
  return [
    subTitle('Anhänge'),
    { ul: docs.map((a) => ({ text: a.name, fontSize: 8.5, color: '#1d4ed8', link: a.file_url ?? undefined })), margin: [4, 0, 0, 6] } as Content,
  ]
}

async function programmeItems(h: TrainingSessionHandout, p: Palette, renderHtml: HandoutPdfOptions['renderHtml']): Promise<Content[]> {
  const items = h.blocks
    .filter((b) => b.kind !== 'station' && (b.content || b.learning_objective || b.safety_notes || b.attachments?.length))
    .sort(byStart)
  if (!items.length) return []
  const out: Content[] = [{ ...sectionTitle('Gemeinsame Programmpunkte', p), pageBreak: 'before' }]
  for (const b of items) {
    const meta = [
      timeSpan(b.start_offset_minutes, blockEnd(b), h.start_time),
      b.groups?.length ? b.groups.map((g) => g.name).join(', ') : 'Alle Gruppen',
      b.location,
      (b.instructors ?? []).map((i) => i.name).join(', '),
    ].filter(Boolean).join('  ·  ')
    const body: Content[] = [
      { text: b.title, fontSize: 11, bold: true },
      { text: meta, fontSize: 8, color: MUTED, margin: [0, 1, 0, 6] },
    ]
    if (b.learning_objective) body.push(note('Lernziel', b.learning_objective, p.brand))
    if (b.safety_notes) body.push(note('Sicherheit', b.safety_notes, WARN))
    if (b.content && renderHtml) body.push(...(await renderHtml(b.content)))
    body.push(...attachmentList(b))
    out.push({ stack: body, margin: [0, 0, 0, 14] } as Content)
  }
  return out
}

function materialPage(h: TrainingSessionHandout, p: Palette): Content[] {
  const lines = materialSummary(h.blocks)
  const out: Content[] = []
  if (lines.length) {
    out.push({ ...sectionTitle('Packliste', p), pageBreak: 'before' })
    out.push({ text: 'Planungswerte: Material einer Station zählt einmal, weil die Gruppen nacheinander üben. Bestand wird nicht gebucht.', fontSize: 8, color: MUTED, margin: [0, 0, 0, 6] })
    out.push({
      table: {
        headerRows: 1,
        dontBreakRows: true,
        widths: [9, 32, '*', '*'],
        body: [
          ['', th('Menge'), th('Material'), th('Verwendet bei')],
          ...lines.map((line) => [checkbox(), { text: String(line.quantity), bold: true, alignment: 'right' }, line.label, { text: line.usedAt.join(', '), color: MUTED }]),
        ],
      },
      layout: tableLayout(p),
      fontSize: 9,
      margin: [0, 0, 0, 16],
    } as Content)
  }
  if (h.notes) {
    out.push({ ...sectionTitle('Anmerkungen', p), ...(lines.length ? {} : { pageBreak: 'before' as const }) })
    out.push({ text: h.notes, fontSize: 9, lineHeight: 1.35 })
  }
  return out
}

// ── Document ─────────────────────────────────────────────────────────────────

export async function buildHandoutPdf(h: TrainingSessionHandout, options: HandoutPdfOptions = {}): Promise<TDocumentDefinitions> {
  const theme: HandoutTheme = { brandColor: '', orgName: '', logo: null, ...options.theme }
  const p = palette(theme.brandColor)
  const lanes = handoutLanes(h)
  const cards = stationCards(h.blocks)

  // Page 1: header, facts and section title take ~130pt plus extra title lines; the overview gets the rest.
  const titleLines = wrap(h.title, CONTENT_WIDTH - (theme.logo ? 52 : 0), 19, 3, true).length
  const overviewRoom = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - 130 - (titleLines - 1) * 23

  const content: Content[] = [...hero(h, theme, p), facts(h, lanes, cards)]
  if (h.blocks.length) content.push(sectionTitle('Ablaufplan', p), { svg: swimlaneSvg(h, lanes, p, overviewRoom), width: CONTENT_WIDTH } as Content)

  content.push({ stack: [...assignmentTable(h, p), ...routeTables(h, lanes, p)], pageBreak: 'before' })

  for (const [i, card] of cards.entries()) {
    const first = h.blocks.find((b) => b.id === card.blockId)
    content.push(...(await stationSheet(card, i, cards.length, first, h, p, options.renderHtml)))
  }
  content.push(...(await programmeItems(h, p, options.renderHtml)))
  content.push(...materialPage(h, p))

  const stand = h.updated_at
    ? new Date(h.updated_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : ''
  const shortDate = new Date(h.date).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const brandBar = { canvas: [{ type: 'rect', x: 0, y: 0, w: PAGE_WIDTH, h: 3, color: p.brand }] }

  return {
    pageSize: 'A4',
    pageMargins: [MARGIN_X, MARGIN_TOP, MARGIN_X, MARGIN_BOTTOM],
    info: { title: h.title, subject: 'Ausbildungsplan', creator: theme.orgName || 'JF-Manager' },
    ...(theme.logo && 'image' in theme.logo ? { images: { logo: theme.logo.image } } : {}),
    defaultStyle: { font: 'Roboto', fontSize: 9, color: INK, lineHeight: 1.2 },
    styles: { body: { fontSize: 9, lineHeight: 1.35, margin: [0, 0, 0, 5] } },
    // Page 1 carries the full header; later pages a slim running head.
    header: (page: number) => (page === 1 ? brandBar : {
      stack: [
        brandBar,
        {
          columns: [
            ...(theme.logo ? [{ ...logoNode(theme.logo, 14), width: 'auto', margin: [0, 0, 6, 0] }] : []),
            { text: theme.orgName, fontSize: 7.5, color: MUTED, margin: [0, 3, 0, 0] },
            { text: `${h.title}  ·  ${shortDate}`, fontSize: 7.5, color: MUTED, alignment: 'right', margin: [0, 3, 0, 0] },
          ],
          margin: [MARGIN_X, 14, MARGIN_X, 0],
        },
      ],
    }) as Content,
    footer: (page: number, pages: number) => ({
      columns: [
        { text: `Version ${h.revision}${stand ? ` · Stand ${stand}` : ''}`, fontSize: 6.5, color: MUTED },
        { text: `${page} / ${pages}`, fontSize: 6.5, color: MUTED, alignment: 'right' },
      ],
      margin: [MARGIN_X, 16, MARGIN_X, 0],
    }) as Content,
    content,
  } as TDocumentDefinitions
}
