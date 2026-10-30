import { describe, expect, it } from 'vitest'
import type { TrainingBlock, TrainingSessionHandout } from '@/types/training'
import { resolveBrand } from '@/theme/brand'
import { BRAND_MARK_SVG } from '@/theme/brandMark'
import { buildHandoutPdf } from '../handoutPdf'
import { blockLaneRuns, clockTime, handoutLanes, instructorAssignments } from '../handoutSummary'
import { htmlToPdfContent } from '../handoutPdfHtml'

let id = 1
const block = (title: string, start: number, extra: Partial<TrainingBlock> = {}): TrainingBlock => ({
  id: id++, title, content: '', session: 1, groups: [], library_block: null, library_block_title: null,
  duration_minutes: 25, start_offset_minutes: start, position_order: 0, color: '', nextcloud_folder_url: '',
  created_at: '', updated_at: '', media: [], attachments: [], kind: 'block', ...extra,
})
const a = { id: 1, name: 'Bambini' }
const b = { id: 2, name: 'Jugend' }
const c = { id: 3, name: 'Ältere' }
const toni = { id: 7, name: 'Toni Trainer' }

const handout = (blocks: TrainingBlock[], groups = [a, b, c]): TrainingSessionHandout => ({
  id: 1, revision: 2, status: 'published', title: 'Stationsausbildung', description: '', date: '2026-11-07',
  start_time: '09:00:00', end_time: '11:00:00', location: 'Gerätehaus', notes: '', groups, blocks,
})

const json = (value: unknown) => JSON.stringify(value)

describe('handoutPdf', () => {
  it('formats clock times from the session start', () => {
    expect(clockTime(75, '09:00:00')).toBe('10:15')
    expect(clockTime(25, null)).toBe('+25′')
  })

  it('uses one lane per group and a single lane without groups', () => {
    expect(handoutLanes(handout([block('X', 0, { groups: [{ id: 9, name: 'Gast' }] })])).map((l) => l.label))
      .toEqual(['Bambini', 'Jugend', 'Ältere', 'Gast'])
    expect(handoutLanes(handout([block('X', 0)], []))).toEqual([{ key: 'all', label: 'Alle Gruppen', groupId: null }])
  })

  it('draws a block for several neighbouring groups as one box', () => {
    const lanes = handoutLanes(handout([]))
    expect(blockLaneRuns(block('Alle', 0), lanes)).toEqual([[0, 2]])
    expect(blockLaneRuns(block('Spiel', 0, { groups: [a, b] }), lanes)).toEqual([[0, 1]])
    expect(blockLaneRuns(block('Getrennt', 0, { groups: [a, c] }), lanes)).toEqual([[0, 0], [2, 2]])
  })

  it('lists who is where, unstaffed stations last', () => {
    const result = instructorAssignments([
      block('Knoten', 30, { kind: 'station', station_key: 'k', groups: [a], instructors: [toni] }),
      block('Knoten', 60, { kind: 'station', station_key: 'k', groups: [b], instructors: [toni] }),
      block('Begrüßung', 0, { instructors: [toni] }),
      block('Erste Hilfe', 30, { kind: 'station', station_key: 'e', groups: [b] }),
    ])
    expect(result.map((r) => r.name)).toEqual(['Toni Trainer', 'unbesetzt'])
    expect(result[0]!.duties).toEqual([
      { title: 'Begrüßung', location: '', slots: [[0, 25]] },
      { title: 'Knoten', location: '', slots: [[30, 55], [60, 85]] },
    ])
  })

  it('gives every station its own sheet and lists unassigned stations', async () => {
    const doc = await buildHandoutPdf(handout([
      block('Begrüßung', 0, { groups: [] }),
      block('Knoten', 30, { kind: 'station', station_key: 'k', groups: [a], instructors: [toni], location: 'Halle' }),
      block('Knoten', 60, { kind: 'station', station_key: 'k', groups: [b], instructors: [toni], location: 'Halle' }),
      block('Erste Hilfe', 30, { kind: 'station', station_key: 'e', groups: [b] }),
    ]))
    const text = json(doc.content)
    expect(text).toContain('STATION 1 VON 2')
    expect(text).toContain('STATION 2 VON 2')
    expect(text).toContain('Wer ist wo?')
    expect(text).toContain('unbesetzt')
    expect(text).toContain('09:30–09:55')
  })

  it('uses the shades the app derives from the chosen colour and ignores invalid colours', async () => {
    const pageOne = async (brandColor: string) => {
      const doc = await buildHandoutPdf(handout([block('X', 0)]), { theme: { brandColor, orgName: 'JF Nord' } })
      return json((doc.header as (page: number) => unknown)(1))
    }
    expect(await pageOne('#0e7490')).toContain(resolveBrand('#0e7490').light.color)
    expect(await pageOne('red; x')).toContain(resolveBrand(null).light.color)
  })

  it('shows the logo on page 1 and in the running head', async () => {
    const svgDoc = await buildHandoutPdf(handout([block('X', 0)]), { theme: { logo: { svg: BRAND_MARK_SVG } } })
    expect(json(svgDoc.content)).toContain('#0b4ea2')
    expect(json((svgDoc.header as (page: number) => unknown)(2))).toContain('#0b4ea2')
    const imageDoc = await buildHandoutPdf(handout([block('X', 0)]), { theme: { logo: { image: 'data:image/png;base64,AA' } } })
    expect(imageDoc.images).toEqual({ logo: 'data:image/png;base64,AA' })
    expect(json(imageDoc.content)).toContain('"image":"logo"')
  })

  it('renders the overview as a scaled svg with escaped titles', async () => {
    const doc = await buildHandoutPdf(handout([block('Knoten & <Stiche>', 0, { groups: [a] })]))
    const svg = json(doc.content).match(/<svg[^]*?<\/svg>/)?.[0] ?? ''
    expect(svg).toContain('Knoten &amp; &lt;Stiche&gt;')
    expect(svg).not.toContain('<Stiche>')
  })
})

describe('htmlToPdfContent', () => {
  it('keeps paragraphs, lists and emphasis', async () => {
    const content = await htmlToPdfContent('<h2>Ablauf</h2><p>Erst <strong>vormachen</strong>, dann üben.</p><ul><li>Mastwurf</li><li>Kreuzknoten</li></ul>', async () => null)
    expect(content).toHaveLength(3)
    expect(content[0]).toMatchObject({ bold: true, text: [{ text: 'Ablauf' }] })
    expect(content[1]).toMatchObject({ text: [{ text: 'Erst ' }, { text: 'vormachen', bold: true }, { text: ', dann üben.' }] })
    expect(json(content[2])).toContain('Kreuzknoten')
  })

  it('embeds loadable images and skips the rest', async () => {
    const content = await htmlToPdfContent('<p><img src="/a.png"><img src="/b.png"></p>', async (src) => (src === '/a.png' ? 'data:image/png;base64,AA' : null))
    expect(content).toEqual([expect.objectContaining({ image: 'data:image/png;base64,AA' })])
  })
})
