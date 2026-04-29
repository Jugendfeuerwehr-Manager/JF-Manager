<template>
  <div class="training-handout" ref="handoutEl">
    <!-- Header -->
    <div class="handout-header">
      <div class="handout-title-row">
        <h1 class="handout-title">{{ handout.title }}</h1>
        <div class="handout-meta">
          <span>{{ formatDate(handout.date) }}</span>
          <span v-if="handout.start_time">· {{ handout.start_time }}</span>
          <span v-if="handout.end_time">– {{ handout.end_time }}</span>
          <span v-if="handout.location">· {{ handout.location }}</span>
        </div>
      </div>

      <div v-if="handout.groups?.length" class="handout-groups">
        Gruppen: <strong>{{ handout.groups.map((g) => g.name).join(', ') }}</strong>
      </div>
    </div>

    <!-- Schedule overview -->
    <section class="schedule-section no-print-break">
      <h2>Übungsablauf</h2>
      <table class="schedule-table">
        <thead>
          <tr>
            <th>Zeit</th>
            <th>Ausbildungspunkt</th>
            <th>Dauer</th>
            <th>Gruppe</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="block in handout.blocks" :key="block.id">
            <td class="time-col">{{ offsetToTime(block.start_offset_minutes, handout.start_time) }}</td>
            <td>{{ block.title }}</td>
            <td>{{ block.duration_minutes }} Min.</td>
            <td>{{ block.groups?.length ? block.groups.map((g) => g.name).join(', ') : 'Alle' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Static Swimlane overview -->
    <section v-if="handout.blocks.length" class="swimlane-section no-print-break">
      <h2>Ablauf-Übersicht</h2>
      <div class="swimlane-wrap" :style="{ height: swimlaneHeight + 'px' }">
        <!-- Time ruler -->
        <div class="sl-ruler">
          <template v-for="tick in swimlaneTicks" :key="tick.offset">
            <div class="sl-tick" :style="{ top: tick.px + 'px' }">{{ offsetToTime(tick.offset, handout.start_time) }}</div>
            <div class="sl-line" :style="{ top: tick.px + 'px', opacity: tick.offset % 60 === 0 ? 1 : 0.4 }" />
          </template>
        </div>
        <!-- Lane columns -->
        <div class="sl-lanes">
          <div v-for="lane in swimlaneLanes" :key="lane.key" class="sl-lane">
            <div class="sl-lane-header">{{ lane.label }}</div>
            <div class="sl-lane-body" :style="{ height: swimlaneHeight + 'px' }">
              <div
                v-for="block in lane.blocks"
                :key="block.id"
                class="sl-block"
                :style="{
                  top: (block.start_offset_minutes ?? 0) * SCALE + 'px',
                  height: Math.max(20, block.duration_minutes * SCALE) + 'px',
                  background: block.color ? block.color + '33' : '#dbeafe',
                  borderColor: block.color ?? '#3b82f6',
                }"
              >
                <span class="sl-block-title">{{ block.title }}</span>
                <span class="sl-block-dur">{{ block.duration_minutes }}'</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Per-block details -->
    <section
      v-for="block in handout.blocks"
      :key="`detail-${block.id}`"
      class="block-detail"
    >
      <div class="block-detail-header">
        <div class="block-detail-color" :style="{ background: block.color ?? 'var(--primary-color)' }" />
        <h3 class="block-detail-title">{{ block.title }}</h3>
        <span class="block-detail-duration text-color-secondary text-sm">{{ block.duration_minutes }} Min.</span>
      </div>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-if="block.content" class="block-detail-content prose" v-html="block.content" />
    </section>

    <!-- Notes -->
    <section v-if="handout.notes" class="notes-section">
      <h2>Notizen</h2>
      <p>{{ handout.notes }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TrainingSessionHandout, TrainingBlock } from '@/types/training'

interface Props {
  handout: TrainingSessionHandout
}

const props = defineProps<Props>()

const SCALE = 2 // px per minute

// ── Static swimlane ──────────────────────────────────────────────────────────

const swimlaneLanes = computed(() => {
  const map = new Map<string, { key: string; label: string; blocks: TrainingBlock[] }>()

  const allBlocks = props.handout.blocks.filter((b) => !b.groups?.length)
  if (allBlocks.length) map.set('all', { key: 'all', label: 'Alle Gruppen', blocks: allBlocks })

  for (const block of props.handout.blocks) {
    for (const g of block.groups ?? []) {
      if (!map.has(String(g.id))) map.set(String(g.id), { key: String(g.id), label: g.name, blocks: [] })
      map.get(String(g.id))!.blocks.push(block)
    }
  }

  return [...map.values()]
})

const swimlaneMaxMin = computed(() => {
  if (!props.handout.blocks.length) return 60
  return Math.max(...props.handout.blocks.map((b) => (b.start_offset_minutes ?? 0) + b.duration_minutes))
})

const swimlaneHeight = computed(() => swimlaneMaxMin.value * SCALE)

const swimlaneTicks = computed(() => {
  const ticks: { offset: number; px: number }[] = []
  for (let t = 0; t <= swimlaneMaxMin.value; t += 15) {
    ticks.push({ offset: t, px: t * SCALE })
  }
  return ticks
})

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function offsetToTime(offsetMinutes: number | null | undefined, startTime?: string | null): string {
  if (!startTime || offsetMinutes == null) return offsetMinutes ? `+${offsetMinutes}m` : '—'
  const parts = startTime.split(':')
  const h = Number(parts[0] ?? 0)
  const m = Number(parts[1] ?? 0)
  const totalMinutes = h * 60 + m + offsetMinutes
  const hh = Math.floor(totalMinutes / 60) % 24
  const mm = totalMinutes % 60
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}
</script>

<style scoped>
.training-handout {
  max-width: 860px;
  margin: 0 auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #1a1a1a;
}

.handout-header {
  border-bottom: 3px solid #1d4ed8;
  padding-bottom: 1rem;
  margin-bottom: 1.5rem;
}
.handout-title { font-size: 1.75rem; font-weight: 800; margin: 0 0 0.25rem; }
.handout-meta { font-size: 1rem; color: #555; }
.handout-groups { font-size: 0.95rem; margin-top: 0.5rem; }

.schedule-section { margin-bottom: 2rem; }
.schedule-section h2 { font-size: 1.1rem; font-weight: 700; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; }

.schedule-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.schedule-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}
.schedule-table td {
  padding: 0.4rem 0.75rem;
  border: 1px solid #e2e8f0;
  vertical-align: top;
}
.schedule-table tr:nth-child(even) td { background: #f8fafc; }
.time-col { white-space: nowrap; font-weight: 600; }

.block-detail {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  overflow: hidden;
  page-break-inside: avoid;
}

.block-detail-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.block-detail-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}
.block-detail-title { font-size: 1rem; font-weight: 700; margin: 0; flex: 1; }

.block-detail-content {
  padding: 1rem;
  font-size: 0.9rem;
  line-height: 1.6;
}

.block-detail-content :deep(img) { max-width: 100%; border-radius: 4px; }
.block-detail-content :deep(h1),
.block-detail-content :deep(h2),
.block-detail-content :deep(h3) { font-weight: 700; margin-top: 1rem; }
.block-detail-content :deep(ul),
.block-detail-content :deep(ol) { padding-left: 1.5rem; }

.notes-section {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1.5rem;
}
.notes-section h2 { font-size: 1rem; font-weight: 700; margin: 0 0 0.5rem; }

/* ── Static swimlane ──────────────────────────────────────────────── */
.swimlane-section { margin-bottom: 2rem; page-break-inside: avoid; }
.swimlane-section h2 { font-size: 1.1rem; font-weight: 700; border-bottom: 1px solid #ddd; padding-bottom: 0.25rem; margin-bottom: 0.75rem; }

.swimlane-wrap {
  display: flex;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  font-size: 0.72rem;
}

.sl-ruler {
  width: 52px;
  flex-shrink: 0;
  position: relative;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
}

.sl-tick {
  position: absolute;
  right: 4px;
  transform: translateY(-50%);
  white-space: nowrap;
  color: #64748b;
  font-weight: 600;
}

.sl-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: #94a3b8;
}

.sl-lanes {
  flex: 1;
  display: flex;
  overflow-x: auto;
}

.sl-lane {
  flex: 1;
  min-width: 120px;
  border-right: 1px solid #e2e8f0;
}
.sl-lane:last-child { border-right: none; }

.sl-lane-header {
  height: 24px;
  background: #f1f5f9;
  border-bottom: 2px solid #3b82f6;
  display: flex;
  align-items: center;
  padding: 0 6px;
  font-weight: 700;
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sl-lane-body {
  position: relative;
}

.sl-block {
  position: absolute;
  left: 3px;
  right: 3px;
  border: 1.5px solid #3b82f6;
  border-radius: 4px;
  padding: 2px 4px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}

.sl-block-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sl-block-dur {
  color: #64748b;
  font-size: 0.65rem;
}

@media print {
  .training-handout { max-width: 100%; margin: 0; }
  .no-print-break { page-break-inside: avoid; }
}
</style>
