<template>
  <div class="training-handout">
    <!-- Header: same structure as page 1 of the PDF -->
    <header class="handout-header">
      <img v-if="logoUrl && !logoFailed" class="handout-logo" :src="logoUrl" alt="" @error="logoFailed = true" />
      <BrandMark v-else class="handout-logo" :size="48" />
      <div class="handout-heading">
        <p class="handout-eyebrow">
          <template v-if="orgName">{{ orgName }} · </template>Ausbildungsplan
          <TrainingStatusBadge :status="handout.status" />
        </p>
        <h1 class="handout-title">{{ handout.title }}</h1>
        <p class="handout-meta">
          {{ [formatDate(handout.date), timeRange, handout.location].filter(Boolean).join(' · ') }}
        </p>
      </div>
    </header>

    <p class="handout-facts">
      <span v-for="fact in facts" :key="fact.label"><span class="muted">{{ fact.label }}</span> <strong>{{ fact.value }}</strong></span>
      <strong v-if="openStations" class="warn">{{ openStations }} {{ openStations === 1 ? 'Station' : 'Stationen' }} unbesetzt</strong>
    </p>

    <!-- Swimlane overview: time to scale, a block for several neighbouring groups is one box -->
    <section v-if="handout.blocks.length" class="handout-section overview-section">
      <h2>Ablaufplan</h2>
      <div class="overview-scroll">
        <div class="overview" :style="{ '--lanes': lanes.length }">
          <div class="overview-head">
            <span v-for="lane in lanes" :key="lane.key">{{ lane.label }}</span>
          </div>
          <div class="overview-body" :style="{ height: totalMinutes * SCALE + 'px' }">
            <template v-for="tick in ticks" :key="tick.offset">
              <span class="tick-label" :class="{ full: tick.full }" :style="{ top: tick.offset * SCALE + 'px' }">{{ clockTime(tick.offset, handout.start_time) }}</span>
              <span v-if="tick.offset" class="tick-line" :class="{ full: tick.full }" :style="{ top: tick.offset * SCALE + 'px' }" />
            </template>
            <div class="overview-lanes">
              <span v-for="(lane, i) in lanes" v-show="i > 0" :key="lane.key" class="lane-divider" :style="{ left: `calc(${i} / var(--lanes) * 100%)` }" />
              <div
                v-for="box in boxes"
                :key="box.key"
                class="overview-block"
                :class="{ compact: lineCount(box.block) < 1 }"
                :style="{
                  top: box.block.start_offset_minutes * SCALE + 1 + 'px',
                  height: Math.max(4, box.block.duration_minutes * SCALE - 2) + 'px',
                  left: `calc(${box.from} / var(--lanes) * 100% + 2px)`,
                  width: `calc(${box.to - box.from + 1} / var(--lanes) * 100% - 4px)`,
                  '--block-color': colorOf(box.block),
                }"
                :title="box.block.title"
              >
                <strong>{{ box.block.title }}<span v-if="lineCount(box.block) < 2" class="inline-time">{{ span(box.block) }}</span></strong>
                <span v-if="lineCount(box.block) >= 2">{{ [span(box.block), box.block.location].filter(Boolean).join(' · ') }}</span>
                <span v-if="lineCount(box.block) >= 3 && box.block.instructors?.length">{{ box.block.instructors.map((i) => i.name).join(', ') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Who is where -->
    <section v-if="assignments.length" class="handout-section print-break">
      <h2>Wer ist wo?</h2>
      <div class="table-scroll">
        <table class="handout-table">
          <thead><tr><th>Ausbilder</th><th>Einsatz</th><th>Ort</th><th>Zeit</th></tr></thead>
          <tbody>
            <template v-for="person in assignments" :key="person.id ?? 'open'">
              <tr v-for="(duty, i) in person.duties" :key="`${person.id}-${i}`">
                <th v-if="i === 0" scope="row" :rowspan="person.duties.length" :class="{ warn: person.id === null }">{{ person.name }}</th>
                <td>{{ duty.title }}</td>
                <td :class="{ muted: !duty.location }">{{ duty.location || '—' }}</td>
                <td class="muted nowrap">
                  <span v-for="([s, e], j) in duty.slots" :key="j" class="line">{{ timeSpan(s, e, handout.start_time) }}</span>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Route of every group -->
    <section class="handout-section" :class="{ 'print-break': !assignments.length }">
      <h2>{{ lanes.length > 1 ? 'Laufzettel der Gruppen' : 'Übungsablauf' }}</h2>
      <div v-for="lane in lanes" :key="lane.key" class="route">
        <h3 v-if="lanes.length > 1">{{ lane.label }}</h3>
        <div class="table-scroll">
          <table class="handout-table">
            <thead><tr><th>Zeit</th><th>Programmpunkt</th><th>Ort</th><th>Ausbilder</th></tr></thead>
            <tbody>
              <tr v-for="block in laneBlocks(handout.blocks, lane)" :key="block.id">
                <td class="nowrap"><strong>{{ span(block) }}</strong></td>
                <td><span class="swatch" :style="{ background: colorOf(block) }" />{{ block.title }}</td>
                <td class="muted">{{ block.location }}</td>
                <td class="muted">{{ (block.instructors ?? []).map((i) => i.name).join(', ') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- One sheet per station -->
    <article v-for="(card, index) in cards" :key="card.key" class="handout-section station-sheet print-break" :style="{ '--block-color': colorOf(blockOf(card)) }">
      <header class="station-head">
        <div>
          <p class="handout-eyebrow">Station {{ index + 1 }} von {{ cards.length }}</p>
          <h2 class="station-title">{{ card.title }}</h2>
        </div>
        <p class="station-duration"><strong>{{ slotMinutes(card) }}</strong> Min. je Durchgang</p>
      </header>
      <dl class="station-facts">
        <div><dt>Ort</dt><dd>{{ card.location || '—' }}</dd></div>
        <div>
          <dt>Ausbilder</dt>
          <dd v-if="card.instructors.length">{{ card.instructors.map((i) => i.name).join(', ') }}</dd>
          <dd v-else class="warn">noch nicht besetzt</dd>
        </div>
      </dl>
      <h3>Durchgänge</h3>
      <table class="handout-table">
        <thead><tr><th>Zeit</th><th>Gruppe</th><th>Anwesend</th><th><span class="sr-only">Erledigt</span></th></tr></thead>
        <tbody>
          <tr v-for="(slot, i) in card.slots" :key="i">
            <td class="nowrap"><strong>{{ timeSpan(slot.start, slot.end, handout.start_time) }}</strong></td>
            <td>{{ slot.groups }}</td>
            <td />
            <td class="check-col"><span class="checkbox" /></td>
          </tr>
        </tbody>
      </table>
      <div v-if="card.learningObjective" class="handout-note"><strong>Lernziel</strong><p>{{ card.learningObjective }}</p></div>
      <div v-if="card.safetyNotes" class="handout-note warn-note"><strong>Sicherheit</strong><p>{{ card.safetyNotes }}</p></div>
      <template v-if="card.materials.length">
        <h3>Material</h3>
        <ul class="checklist">
          <li v-for="(m, i) in card.materials" :key="i"><span class="checkbox" /><strong>{{ m.quantity }} ×</strong> {{ m.label }}</li>
        </ul>
      </template>
      <template v-if="blockOf(card)?.content">
        <h3>Ablauf</h3>
        <SafeHtml class="prose" :html="blockOf(card)!.content" />
      </template>
      <HandoutAttachments :attachments="blockOf(card)?.attachments" />
      <div class="print-only">
        <h3>Notizen</h3>
        <div class="note-lines" />
      </div>
    </article>

    <!-- Shared programme items -->
    <section v-if="programme.length" class="handout-section print-break">
      <h2>Gemeinsame Programmpunkte</h2>
      <article v-for="block in programme" :key="block.id" class="programme-item">
        <h3>{{ block.title }}</h3>
        <p class="muted small">
          {{ [span(block), block.groups?.length ? block.groups.map((g) => g.name).join(', ') : 'Alle Gruppen', block.location, (block.instructors ?? []).map((i) => i.name).join(', ')].filter(Boolean).join(' · ') }}
        </p>
        <div v-if="block.learning_objective" class="handout-note"><strong>Lernziel</strong><p>{{ block.learning_objective }}</p></div>
        <div v-if="block.safety_notes" class="handout-note warn-note"><strong>Sicherheit</strong><p>{{ block.safety_notes }}</p></div>
        <SafeHtml v-if="block.content" class="prose" :html="block.content" />
        <HandoutAttachments :attachments="block.attachments" />
      </article>
    </section>

    <!-- Packing list and notes -->
    <section v-if="materials.length" class="handout-section print-break">
      <h2>Packliste</h2>
      <p class="muted small">Planungswerte: Material einer Station zählt einmal, weil die Gruppen nacheinander üben. Bestand wird nicht gebucht.</p>
      <div class="table-scroll">
        <table class="handout-table">
          <thead><tr><th><span class="sr-only">Gepackt</span></th><th>Menge</th><th>Material</th><th>Verwendet bei</th></tr></thead>
          <tbody>
            <tr v-for="line in materials" :key="line.label + line.usedAt.join()">
              <td class="check-col"><span class="checkbox" /></td>
              <td><strong>{{ line.quantity }}</strong></td>
              <td>{{ line.label }}</td>
              <td class="muted">{{ line.usedAt.join(', ') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="handout.notes" class="handout-section" :class="{ 'print-break': !materials.length }">
      <h2>Anmerkungen</h2>
      <p class="notes">{{ handout.notes }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import BrandMark from '@/components/common/BrandMark.vue'
import SafeHtml from '@/components/common/SafeHtml.vue'
import TrainingStatusBadge from '../atoms/TrainingStatusBadge.vue'
import HandoutAttachments from '../molecules/HandoutAttachments.vue'
import { safeBlockColor } from '../utils/blockColor'
import {
  blockEnd, blockLaneRuns, byStart, clockTime, handoutLanes, instructorAssignments, laneBlocks, materialSummary,
  stationCards, timeSpan, type StationCard,
} from '../utils/handoutSummary'
import type { BlockKind, TrainingBlock, TrainingSessionHandout } from '@/types/training'

interface Props {
  handout: TrainingSessionHandout
  orgName?: string
  logoUrl?: string
}

const props = withDefaults(defineProps<Props>(), { orgName: '', logoUrl: '' })

/** px per minute in the overview */
const SCALE = 2.6
/** Height of one text line in an overview box, px */
const BOX_LINE = 14
const NEUTRAL_KINDS: Partial<Record<BlockKind, string>> = { break: '#94a3b8', transition: '#cbd5e1' }

const logoFailed = ref(false)
const lanes = computed(() => handoutLanes(props.handout))
const cards = computed(() => stationCards(props.handout.blocks))
const materials = computed(() => materialSummary(props.handout.blocks))
const assignments = computed(() => instructorAssignments(props.handout.blocks))
const programme = computed(() => props.handout.blocks
  .filter((b) => b.kind !== 'station' && (b.content || b.learning_objective || b.safety_notes || b.attachments?.length))
  .sort(byStart))
const totalMinutes = computed(() => Math.max(30, ...props.handout.blocks.map(blockEnd)))
const openStations = computed(() => cards.value.filter((c) => !c.instructors.length).length)

const timeRange = computed(() => props.handout.start_time
  ? `${props.handout.start_time.slice(0, 5)}${props.handout.end_time ? `–${props.handout.end_time.slice(0, 5)}` : ''} Uhr`
  : '')

const facts = computed(() => {
  const total = props.handout.blocks.length ? Math.max(...props.handout.blocks.map(blockEnd)) : 0
  const hours = Math.floor(total / 60)
  const instructors = new Set(props.handout.blocks.flatMap((b) => (b.instructors ?? []).map((i) => i.id)))
  return [
    { label: 'Dauer', value: hours ? `${hours}:${String(total % 60).padStart(2, '0')} h` : `${total} Min.` },
    ...(lanes.value[0]?.groupId === null ? [] : [{ label: 'Gruppen', value: String(lanes.value.length) }]),
    { label: 'Stationen', value: String(cards.value.length) },
    { label: 'Ausbilder', value: String(instructors.size) },
  ]
})

const boxes = computed(() => [...props.handout.blocks].sort(byStart).flatMap((block) =>
  blockLaneRuns(block, lanes.value).map(([from, to]) => ({ key: `${block.id}-${from}`, block, from, to }))))

const ticks = computed(() => {
  const startMinute = Number(props.handout.start_time?.split(':')[1] ?? 0)
  const result: { offset: number; full: boolean }[] = []
  for (let t = 0; t <= totalMinutes.value; t += 15) result.push({ offset: t, full: (startMinute + t) % 60 === 0 })
  return result
})

/** Text lines that fit into a block's box in the overview. */
function lineCount(block: TrainingBlock) {
  return Math.floor((block.duration_minutes * SCALE - 6) / BOX_LINE)
}

function span(block: TrainingBlock) {
  return timeSpan(block.start_offset_minutes, blockEnd(block), props.handout.start_time)
}

function colorOf(block: TrainingBlock | undefined) {
  if (!block) return 'var(--p-primary-color)'
  return safeBlockColor(block.color) ?? NEUTRAL_KINDS[block.kind ?? 'block'] ?? 'var(--p-primary-color)'
}

function blockOf(card: StationCard) {
  return props.handout.blocks.find((b) => b.id === card.blockId)
}

function slotMinutes(card: StationCard) {
  const slot = card.slots[0]
  return slot ? slot.end - slot.start : 0
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}
</script>

<style scoped>
.training-handout {
  --handout-warn: var(--p-amber-700, #b45309);
  min-width: 0;
  overflow-wrap: anywhere;
  max-width: 960px;
  margin: 0 auto;
  box-sizing: border-box;
  padding: var(--jf-space-3) var(--jf-space-4) var(--jf-space-4);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  /* Sheet on the page ground, like a printed handout */
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font-size: 0.9rem;
}

@media (max-width: 640px) {
  .training-handout { padding: var(--jf-space-2); }
}

.muted { color: var(--jf-color-text-muted); }
.small { font-size: 0.8rem; }
.warn { color: var(--handout-warn); }
.nowrap { white-space: nowrap; }
.line { display: block; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

/* ── Header ──────────────────────────────────────────────────────────── */
.handout-header {
  display: flex;
  gap: var(--jf-space-2);
  align-items: flex-start;
  padding-top: var(--jf-space-2);
  border-top: 3px solid var(--p-primary-color);
}
.handout-logo { width: 48px; height: 48px; object-fit: contain; flex-shrink: 0; }
.handout-heading { min-width: 0; }
.handout-eyebrow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-primary-color);
}
.handout-title { margin: 0.15rem 0; font-size: 1.6rem; font-weight: 700; line-height: 1.2; }
.handout-meta { margin: 0; color: var(--jf-color-text-muted); }

.handout-facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5) var(--jf-space-3);
  margin: var(--jf-space-2) 0 0;
  padding-top: var(--jf-space-1);
  border-top: 1px solid var(--jf-color-border);
  font-size: 0.85rem;
}

/* ── Sections ────────────────────────────────────────────────────────── */
.handout-section { margin-top: var(--jf-space-4); }
.handout-section h2 { margin: 0 0 var(--jf-space-1-5); font-size: 1.15rem; font-weight: 700; }
.handout-section > h2::after {
  content: '';
  display: block;
  width: 1.5rem;
  height: 2px;
  margin-top: 0.3rem;
  background: var(--p-primary-color);
}
.handout-section h3 { margin: var(--jf-space-2) 0 var(--jf-space-1); font-size: 0.95rem; font-weight: 700; }

.table-scroll { overflow-x: auto; }
.handout-table { width: 100%; border-collapse: collapse; }
.handout-table thead th {
  padding: 0.35rem 0.5rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-align: left;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
  border-bottom: 1px solid color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
.handout-table td,
.handout-table tbody th {
  padding: 0.4rem 0.5rem;
  vertical-align: top;
  text-align: left;
  border-bottom: 1px solid var(--jf-color-border);
}
.swatch { display: inline-block; width: 0.55rem; height: 0.55rem; margin-right: 0.45rem; border-radius: 2px; }
.route + .route { margin-top: var(--jf-space-1); }

/* ── Overview ────────────────────────────────────────────────────────── */
.overview-scroll { overflow-x: auto; }
.overview { --axis: 2.75rem; min-width: calc(var(--axis) + var(--lanes) * 8rem); }
.overview-head {
  display: grid;
  grid-template-columns: repeat(var(--lanes), minmax(0, 1fr));
  margin-left: var(--axis);
  border-bottom: 2px solid var(--p-primary-color);
}
.overview-head span {
  padding: 0 0.3rem 0.25rem;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.overview-body { position: relative; margin-bottom: var(--jf-space-1); }
.tick-label {
  position: absolute;
  left: 0;
  width: calc(var(--axis) - 0.4rem);
  transform: translateY(-50%);
  font-size: 0.7rem;
  text-align: right;
  color: var(--jf-color-text-muted);
}
.tick-label:first-child { transform: none; }
.tick-label.full { font-weight: 700; color: var(--jf-color-text); }
.tick-line { position: absolute; left: var(--axis); right: 0; border-top: 1px dashed var(--jf-color-border); }
.tick-line.full { border-top-style: solid; }
.overview-lanes { position: absolute; inset: 0 0 0 var(--axis); }
.lane-divider { position: absolute; top: 0; bottom: 0; border-left: 1px solid var(--jf-color-border); }
.overview-block {
  position: absolute;
  display: flex;
  flex-direction: column;
  padding: 0.1rem 0.35rem 0 0.5rem;
  overflow: hidden;
  box-sizing: border-box;
  border-left: 3px solid var(--block-color);
  border-radius: 0 3px 3px 0;
  background: color-mix(in srgb, var(--block-color) 12%, var(--jf-color-card));
  font-size: 0.7rem;
  line-height: 1.3;
}
.overview-block strong { display: flex; gap: 0.5rem; font-size: 0.75rem; }
.overview-block.compact { padding-top: 0; font-size: 0.6rem; line-height: 1; justify-content: center; }
.overview-block.compact strong { font-size: 0.6rem; }
.inline-time { margin-left: auto; font-weight: 400; color: var(--jf-color-text-muted); }
.overview-block > * { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.overview-block span { color: var(--jf-color-text-muted); }

/* ── Station sheet ───────────────────────────────────────────────────── */
.station-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: var(--jf-space-1);
  padding-bottom: var(--jf-space-1);
  border-bottom: 2px solid var(--block-color);
}
.station-head .station-title { margin: 0; }
.station-duration { margin: 0; color: var(--jf-color-text-muted); font-size: 0.8rem; }
.station-duration strong { font-size: 1.2rem; color: var(--jf-color-text); }
.station-facts { display: flex; flex-wrap: wrap; gap: var(--jf-space-1) var(--jf-space-4); margin: var(--jf-space-1-5) 0 0; }
.station-facts dt {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}
.station-facts dd { margin: 0; font-weight: 700; }
.check-col { width: 1.5rem; }
.checkbox {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  border: 1px solid var(--jf-color-text-muted);
  border-radius: 2px;
  vertical-align: -0.1rem;
}
.checklist { margin: 0; padding: 0; list-style: none; }
.checklist li { display: flex; align-items: baseline; gap: 0.45rem; padding: 0.15rem 0; }

.handout-note {
  margin-top: var(--jf-space-1-5);
  padding: 0.1rem 0 0.1rem 0.6rem;
  border-left: 2px solid var(--p-primary-color);
}
.handout-note strong { font-size: 0.75rem; color: var(--p-primary-color); }
.handout-note p { margin: 0.1rem 0 0; }
.warn-note { border-left-color: var(--handout-warn); }
.warn-note strong { color: var(--handout-warn); }

.programme-item + .programme-item { margin-top: var(--jf-space-3); }
.programme-item h3 { margin: 0; }
.programme-item > .muted { margin: 0.1rem 0 0; }

.prose { line-height: 1.6; }
.prose :deep(img) { max-width: 100%; border-radius: 4px; }
.prose :deep(ul), .prose :deep(ol) { padding-left: 1.5rem; }

.notes { white-space: pre-line; margin: 0; }
.print-only { display: none; }

@media print {
  .training-handout {
    max-width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: #ffffff;
    color: #1e293b;
    font-size: 9.5pt;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }
  .overview { min-width: 0; }
  .overview-section, .station-sheet table, .route { break-inside: avoid; }
  .print-break { break-before: page; margin-top: 0; }
  .handout-section h2, .handout-section h3 { break-after: avoid; }
  .print-only { display: block; }
  .note-lines {
    height: 90px;
    background: repeating-linear-gradient(to bottom, transparent 0 17px, #cbd5e1 17px 18px);
  }
}
</style>
