<template>
  <div class="handout-page">
    <div class="handout-toolbar">
      <Button icon="pi pi-arrow-left" text @click="$router.back()" label="Zurück" />
      <div class="spacer" />
      <Button icon="pi pi-print" label="Drucken" outlined size="small" @click="printPage" />
      <Button icon="pi pi-file-pdf" label="PDF herunterladen" size="small" :loading="generatingPdf" @click="downloadPdf" />
    </div>

    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
    </div>

    <div v-else-if="handout" id="handout-print-area">
      <TrainingHandout :handout="handout" />
    </div>

    <div v-else class="error-state">
      <p>Handout konnte nicht geladen werden.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import TrainingHandout from '@/components/training/organisms/TrainingHandout.vue'
import { useTrainingStore } from '@/stores/training'
import type { Content, ContentText } from 'pdfmake/interfaces'

const route = useRoute()
const trainingStore = useTrainingStore()
const generatingPdf = ref(false)
const sessionId = computed(() => Number(route.params.id))
const handout = computed(() => trainingStore.handout)
const loading = computed(() => trainingStore.loading)

onMounted(() => trainingStore.fetchHandout(sessionId.value))

function printPage() {
  window.print()
}

/** Returns true if the hex color is perceived as light (prefer dark text on it). */
function isLightColor(hex: string): boolean {
  const c = hex.replace('#', '')
  if (c.length !== 6) return true
  const r = parseInt(c.slice(0, 2), 16)
  const g = parseInt(c.slice(2, 4), 16)
  const b = parseInt(c.slice(4, 6), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 128
}

/** Fetches an image URL and returns a base64 data URL, or null on error. */
async function fetchImageDataUrl(src: string): Promise<string | null> {
  try {
    const resp = await fetch(src, { credentials: 'include' })
    if (!resp.ok) return null
    const blob = await resp.blob()
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => resolve(null)
      reader.readAsDataURL(blob)
    })
  } catch {
    return null
  }
}

/** Converts an HTML string to pdfmake Content items; embeds <img> as data URLs. */
async function htmlToPdfContent(html: string): Promise<Content[]> {
  const result: Content[] = []
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')

  async function walk(node: Node) {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent?.trim()
      if (text) result.push({ text, style: 'body' } as ContentText)
      return
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return
    const el = node as HTMLElement
    if (el.tagName === 'IMG') {
      const src = (el as HTMLImageElement).src
      if (src) {
        const dataUrl = await fetchImageDataUrl(src)
        if (dataUrl) {
          result.push({ image: dataUrl, width: 400, margin: [0, 4, 0, 8] } as unknown as Content)
        }
      }
      return
    }
    if (el.tagName === 'BR') {
      result.push({ text: '\n' } as ContentText)
      return
    }
    for (const child of Array.from(node.childNodes)) {
      await walk(child)
    }
  }

  for (const child of Array.from(doc.body.childNodes)) {
    await walk(child)
  }
  return result
}

async function downloadPdf() {
  generatingPdf.value = true
  try {
    const { default: pdfMake } = await import('pdfmake/build/pdfmake')
    const { default: pdfFonts } = await import('pdfmake/build/vfs_fonts')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pdfMakeTyped = pdfMake as any
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    pdfMakeTyped.vfs = (pdfFonts as any).pdfMake?.vfs ?? (pdfFonts as any).vfs

    if (!handout.value) return
    const h = handout.value
    const dateStr = new Date(h.date).toLocaleDateString('de-DE', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    })

    // ── Group blocks by swimlane ───────────────────────────────────────────
    type LaneGroup = { key: string; label: string; blocks: typeof h.blocks }
    const laneMap = new Map<string, LaneGroup>()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const allGroupBlocks = h.blocks.filter((b) => !(b as any).groups?.length)
    if (allGroupBlocks.length) {
      laneMap.set('all', { key: 'all', label: 'Alle Gruppen', blocks: allGroupBlocks })
    }
    for (const block of h.blocks) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      for (const g of (block as any).groups ?? []) {
        if (!laneMap.has(String(g.id))) {
          laneMap.set(String(g.id), { key: String(g.id), label: g.name as string, blocks: [] })
        }
        laneMap.get(String(g.id))!.blocks.push(block)
      }
    }
    const laneGroups = [...laneMap.values()]
    const hasMultipleLanes = laneGroups.length > 1

    /** Builds the "Übungsablauf" schedule table for a given set of blocks. */
    function buildScheduleTable(blocks: typeof h.blocks, showGroupColumn: boolean): Content {
      return {
        table: {
          headerRows: 1,
          widths: showGroupColumn ? [60, '*', 60, 80] : [60, '*', 60],
          body: [
            (showGroupColumn
              ? ['Zeit', 'Ausbildungspunkt', 'Dauer', 'Gruppe']
              : ['Zeit', 'Ausbildungspunkt', 'Dauer']
            ).map((label) => ({ text: label, bold: true, fillColor: '#f1f5f9' })),
            ...blocks.map((b) => {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const groupNames = (b as any).groups?.length
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ? (b as any).groups.map((g: { name: string }) => g.name).join(', ')
                : 'Alle'
              const row = [
                offsetToTime(b.start_offset_minutes, h.start_time),
                b.title,
                `${b.duration_minutes} Min.`,
              ]
              if (showGroupColumn) row.push(groupNames)
              return row
            }),
          ],
        },
        margin: [0, 0, 0, 16],
      } as unknown as Content
    }

    // ── First page: title + meta + Ablaufplan (swimlane overview) ─────────
    const content: Content[] = [
      { text: h.title, style: 'h1' } as ContentText,
      {
        text: `${dateStr}${h.start_time ? ' · ' + h.start_time : ''}${h.location ? ' · ' + h.location : ''}`,
        style: 'meta',
      } as ContentText,
      { text: '\n' } as ContentText,
    ]

    // Single-group: show the Übungsablauf on the first page directly
    if (!hasMultipleLanes) {
      content.push({ text: 'Übungsablauf', style: 'h2' } as ContentText)
      content.push(buildScheduleTable(h.blocks, false))
    }

    // ── Ablaufplan swimlane table (only when multiple groups exist) ────────
    if (hasMultipleLanes) {
      // Collect all unique time boundaries (block starts + ends)
      const timeBoundaries = new Set<number>()
      for (const block of h.blocks) {
        const s = block.start_offset_minutes ?? 0
        timeBoundaries.add(s)
        timeBoundaries.add(s + (block.duration_minutes ?? 0))
      }
      const sortedTimes = [...timeBoundaries].sort((a, b) => a - b)

      const tableHeader = [
        { text: 'Zeit', bold: true, fillColor: '#f1f5f9', fontSize: 9 },
        ...laneGroups.map((lane) => ({ text: lane.label, bold: true, fillColor: '#f1f5f9', fontSize: 9 })),
      ]

      // covered: cells already accounted for by a rowSpan above
      const covered = new Set<string>()
      const tableRows: unknown[][] = [tableHeader]

      for (let i = 0; i < sortedTimes.length - 1; i++) {
        const tStart = sortedTimes[i]!
        const tEnd = sortedTimes[i + 1]!
        const row: unknown[] = [{ text: offsetToTime(tStart, h.start_time), fontSize: 8, color: '#64748b' }]

        for (let j = 0; j < laneGroups.length; j++) {
          if (covered.has(`${i}_${j}`)) {
            row.push('') // Placeholder required by pdfmake for rowSpan cells
            continue
          }
          const lane = laneGroups[j]!
          const block = lane.blocks.find((b) => {
            const bS = b.start_offset_minutes ?? 0
            return bS <= tStart && bS + (b.duration_minutes ?? 0) >= tEnd
          })
          if (block && (block.start_offset_minutes ?? 0) === tStart) {
            // This interval is the start of the block — calculate rowSpan
            const bEnd = (block.start_offset_minutes ?? 0) + (block.duration_minutes ?? 0)
            let rowSpan = 0
            for (let k = i; k < sortedTimes.length - 1; k++) {
              if ((sortedTimes[k] ?? 0) >= (block.start_offset_minutes ?? 0) && (sortedTimes[k + 1] ?? 0) <= bEnd) {
                rowSpan++
                if (k > i) covered.add(`${k}_${j}`)
              } else {
                break
              }
            }
            const bgColor = block.color ?? '#3b82f6'
            row.push({
              text: block.title,
              fillColor: bgColor,
              color: isLightColor(bgColor) ? '#1e293b' : '#ffffff',
              fontSize: 8,
              bold: true,
              ...(rowSpan > 1 ? { rowSpan } : {}),
              margin: [2, 2, 2, 2],
            })
          } else {
            // Block covers interval but started earlier (covered by earlier rowSpan)
            row.push('')
          }
        }
        tableRows.push(row)
      }

      content.push({ text: 'Ablaufplan', style: 'h2' } as ContentText)
      content.push({
        table: {
          headerRows: 1,
          widths: ['auto', ...laneGroups.map(() => '*')],
          body: tableRows,
        },
        layout: 'lightHorizontalLines',
        margin: [0, 0, 0, 16],
      } as unknown as Content)
    }

    // ── Per-lane block details ─────────────────────────────────────────────
    let isFirstLane = true
    for (const lane of laneGroups) {
      if (hasMultipleLanes) {
        content.push({
          text: lane.label,
          style: 'h2',
          ...(isFirstLane ? {} : { pageBreak: 'before' }),
        } as ContentText)
        // Per-group Übungsablauf table
        content.push({ text: 'Übungsablauf', style: 'h3' } as ContentText)
        content.push(buildScheduleTable(lane.blocks, false))
      }
      isFirstLane = false

      for (const block of lane.blocks) {
        const blockColor = block.color ?? '#3b82f6'
        content.push({
          text: `■  ${block.title}  ·  ${block.duration_minutes} Min.`,
          style: 'h3',
          color: blockColor,
          margin: [0, 8, 0, 4],
        } as ContentText)

        if (block.content) {
          const blockContent = await htmlToPdfContent(block.content)
          content.push(...blockContent)
        }

        // ── Attached printable documents ──────────────────────────────────
        if (block.attachments && block.attachments.length) {
          const printableExts = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.odt', '.odp', '.ods']
          const printableDocs = block.attachments.filter((att) => {
            if (!att.file_url) return false
            const lower = att.name.toLowerCase()
            return printableExts.some((ext) => lower.endsWith(ext))
          })
          if (printableDocs.length) {
            content.push({
              text: 'Anhänge:',
              fontSize: 9,
              bold: true,
              color: '#64748b',
              margin: [0, 4, 0, 2],
            } as unknown as Content)
            content.push({
              ul: printableDocs.map((att) => ({
                text: att.name,
                color: '#2563eb',
                decoration: 'underline',
                fontSize: 9,
                // link only works for absolute URLs in pdfmake
                link: att.file_url ?? undefined,
              })),
              margin: [8, 0, 0, 8],
            } as unknown as Content)
          }
        }
      }
    }

    // ── Notes ──────────────────────────────────────────────────────────────
    if (h.notes) {
      content.push({ text: 'Anmerkungen', style: 'h2', pageBreak: 'before' } as ContentText)
      content.push({ text: h.notes, style: 'body' } as ContentText)
    }

    const docDef = {
      content,
      styles: {
        h1: { fontSize: 20, bold: true, margin: [0, 0, 0, 4] },
        h2: { fontSize: 14, bold: true, margin: [0, 12, 0, 6] },
        h3: { fontSize: 12, bold: true, margin: [0, 10, 0, 4] },
        meta: { fontSize: 10, color: '#666', margin: [0, 0, 0, 12] },
        body: { fontSize: 10, lineHeight: 1.4, margin: [0, 0, 0, 8] },
      },
      pageMargins: [40, 40, 40, 40] as [number, number, number, number],
    }

    pdfMakeTyped.createPdf(docDef).download(`handout-${sessionId.value}.pdf`)
  } finally {
    generatingPdf.value = false
  }
}

function offsetToTime(offsetMinutes: number | null | undefined, startTime?: string | null): string {
  if (!startTime || offsetMinutes == null) return '—'
  const parts = startTime.split(':')
  const h = Number(parts[0] ?? 0)
  const m = Number(parts[1] ?? 0)
  const total = h * 60 + m + offsetMinutes
  return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}
</script>

<style scoped>
.handout-page { display: flex; flex-direction: column; min-height: 100vh; }

.handout-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
  flex-shrink: 0;
}
.spacer { flex: 1; }

#handout-print-area { padding: 1.5rem; max-width: 960px; margin: 0 auto; }

.loading-state, .error-state {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

@media print {
  .handout-toolbar { display: none; }
  #handout-print-area { padding: 0; max-width: 100%; }
  .handout-page { min-height: auto; }
}
</style>
