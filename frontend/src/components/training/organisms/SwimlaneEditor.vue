<template>
  <div class="swimlane-editor">

    <!-- ── Topbar ──────────────────────────────────────────────────── -->
    <div class="editor-topbar">
      <div class="session-info">
        <span class="session-title">{{ session?.title ?? 'Trainingsplanung' }}</span>
        <span v-if="session?.date" class="session-meta">
          {{ formatDate(session.date) }}
          <span v-if="session?.start_time">· ab {{ session.start_time }} Uhr</span>
        </span>
      </div>
      <div class="topbar-actions">
        <Button
          icon="pi pi-arrow-left"
          label="Kalender"
          size="small"
          severity="secondary"
          outlined
          @click="router.push('/training')"
        />
        <Button
          icon="pi pi-cog"
          label="Einstellungen"
          size="small"
          severity="secondary"
          outlined
          @click="showSessionSettings = true"
        />
        <Button
          :icon="showLibraryPicker ? 'pi pi-times' : 'pi pi-book'"
          :label="showLibraryPicker ? 'Schließen' : 'Bibliothek'"
          size="small"
          :severity="showLibraryPicker ? 'primary' : 'secondary'"
          :outlined="!showLibraryPicker"
          @click="showLibraryPicker = !showLibraryPicker"
        />
        <Button
          icon="pi pi-save"
          label="Speichern"
          size="small"
          :loading="plannerStore.saving"
          :disabled="!isDirty"
          @click="saveAll"
        />
        <Button
          icon="pi pi-file-pdf"
          label="Handout"
          size="small"
          severity="secondary"
          outlined
          @click="goHandout"
        />
      </div>
    </div>

    <!-- ── Main planner ────────────────────────────────────────────── -->
    <div class="planner-container">

      <!-- Scrollable area: headers + grid -->
      <div class="planner-scroll" ref="plannerScroll">

        <!-- Sticky header row -->
        <div class="header-row">
          <div class="time-corner">Zeit</div>
          <div
            v-for="lane in visibleLanes"
            :key="lane.key"
            class="lane-header-cell"
          >
            {{ lane.label }}
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="plannerStore.loading" class="loading-overlay">
          <i class="pi pi-spin pi-spinner" style="font-size: 2rem; color: var(--primary-color)"></i>
          <span>Lade Trainingsplan...</span>
        </div>

        <!-- Grid: ruler + lanes (scroll together) -->
        <div v-else class="grid-body" :style="{ height: totalHeightPx + 'px' }">

          <!-- Time ruler column (sticky left) -->
          <div class="time-ruler">
            <template v-for="tick in timeTicks" :key="tick.offsetMin">
              <div
                v-if="tick.labeled"
                class="ruler-label"
                :style="{ top: tick.px + 'px' }"
              >{{ tick.displayTime }}</div>
              <div
                class="ruler-hline"
                :class="{
                  'ruler-hline--hour': tick.major,
                  'ruler-hline--quarter': tick.labeled && !tick.major,
                }"
                :style="{ top: tick.px + 'px' }"
              />
            </template>
          </div>

          <!-- Lane columns -->
          <div class="lanes-wrap">
            <div
              v-for="lane in visibleLanes"
              :key="lane.key"
              class="lane-col"
              :data-group-id="lane.key"
              @mousedown="onLaneMouseDown($event, lane.key, lane.groupId)"
              @dragover.prevent
              @drop="onLaneDrop($event, lane.groupId)"
            >
              <!-- Background grid lines -->
              <div
                v-for="tick in timeTicks"
                :key="`gl-${tick.offsetMin}`"
                class="grid-line"
                :class="{
                  'grid-line--hour': tick.major,
                  'grid-line--quarter': tick.labeled && !tick.major,
                }"
                :style="{ top: tick.px + 'px' }"
              />

              <!-- Drag-to-create preview -->
              <div
                v-if="creating && creating.laneKey === lane.key"
                class="create-preview"
                :style="createPreviewStyle"
              >
                <span class="create-preview__label">{{ createDuration }} min · Ziehen zum Anpassen</span>
              </div>

              <!-- Block tiles -->
              <TrainingBlockTile
                v-for="block in lane.blocks"
                :key="block.id"
                :block="block"
                :minute-height="MINUTE_PX"
                :selected="selectedBlockId === block.id"
                @click="openEdit(block)"
                @edit="openEdit(block)"
                @remove="plannerStore.removeBlock($event)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Library picker sidebar -->
      <Transition name="slide-panel">
        <div v-if="showLibraryPicker" class="library-panel">
          <LibraryBlockPicker @pick="addFromLibrary" @close="showLibraryPicker = false" />
        </div>
      </Transition>
    </div>

    <!-- Session settings dialog -->
    <Dialog
      v-model:visible="showSessionSettings"
      header="Training bearbeiten"
      :style="{ width: '640px' }"
      modal
    >
      <TrainingSessionForm
        v-if="session"
        :initial-data="(session as TrainingSessionDetail)"
        @success="onSessionSaved"
        @cancel="showSessionSettings = false"
      />
    </Dialog>

    <!-- Block edit dialog -->
    <BlockEditDialog
      v-model:visible="showEditDialog"
      :block="editingBlock"
      @saved="onBlockSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import TrainingBlockTile from '../molecules/TrainingBlockTile.vue'
import LibraryBlockPicker from '../molecules/LibraryBlockPicker.vue'
import BlockEditDialog from '../molecules/BlockEditDialog.vue'
import TrainingSessionForm from '../molecules/TrainingSessionForm.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'
import { useTrainingStore } from '@/stores/training'
import type { PlannerBlock, LibraryBlockList, TrainingSessionDetail } from '@/types/training'
import interact from 'interactjs'

interface Props {
  sessionId: number
}
const props = defineProps<Props>()
const router = useRouter()

const plannerStore = useTrainingPlannerStore()
const trainingStore = useTrainingStore()

// ── Constants ──────────────────────────────────────────────────────────────
const MINUTE_PX = 4      // px per minute → 240 min × 4 = 960 px total
const DISPLAY_MIN = 240  // 4 hours

// ── Refs ───────────────────────────────────────────────────────────────────
const plannerScroll = ref<HTMLElement | null>(null)
const showLibraryPicker = ref(false)
const showEditDialog = ref(false)
const showSessionSettings = ref(false)
const editingBlock = ref<PlannerBlock | null>(null)
const saving = ref(false)

// Drag-to-create state
const creating = ref<{
  laneKey: string
  groupId: number | null
  startPx: number
  currentPx: number
  laneRect: DOMRect
} | null>(null)

// ── Store accessors ────────────────────────────────────────────────────────
const blocks = computed(() => plannerStore.blocks)
const selectedBlockId = computed(() => plannerStore.selectedBlockId)
const isDirty = computed(() => plannerStore.isDirty)
const session = computed(() => trainingStore.currentSession as TrainingSessionDetail | null)
const totalHeightPx = computed(() => DISPLAY_MIN * MINUTE_PX)

// ── Session start time (minutes from midnight) ─────────────────────────────
const sessionStartMin = computed(() => {
  const t = session.value?.start_time
  if (!t) return 8 * 60
  const parts = t.split(':')
  return Number(parts[0] ?? 8) * 60 + Number(parts[1] ?? 0)
})

// ── Time ticks ─────────────────────────────────────────────────────────────
const timeTicks = computed(() => {
  const ticks: { offsetMin: number; px: number; displayTime: string; labeled: boolean; major: boolean }[] = []
  for (let offset = 0; offset <= DISPLAY_MIN; offset += 5) {
    const abs = sessionStartMin.value + offset
    const hh = Math.floor(abs / 60) % 24
    const mm = abs % 60
    ticks.push({
      offsetMin: offset,
      px: offset * MINUTE_PX,
      displayTime: `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`,
      labeled: offset % 15 === 0,
      major: offset % 60 === 0,
    })
  }
  return ticks
})

// ── Visible lanes ──────────────────────────────────────────────────────────
const visibleLanes = computed(() => {
  const groupMap = new Map<number, string>()
  if (session.value?.groups) {
    for (const g of session.value.groups) groupMap.set(g.id, g.name)
  }
  for (const b of blocks.value) {
    for (const gId of b.groupIds) {
      if (!groupMap.has(gId)) groupMap.set(gId, `Gruppe ${gId}`)
    }
  }

  const result: { key: string; groupId: number | null; label: string; blocks: PlannerBlock[] }[] = [
    {
      key: 'all',
      groupId: null,
      label: 'Alle Gruppen',
      blocks: blocks.value.filter((b) => b.allGroups),
    },
  ]

  for (const [gId, gName] of groupMap) {
    result.push({
      key: String(gId),
      groupId: gId,
      label: gName,
      blocks: blocks.value.filter((b) => !b.allGroups && b.groupIds.includes(gId)),
    })
  }

  return result
})

// ── Drag-to-create helpers ─────────────────────────────────────────────────
function snapPx(px: number): number {
  return Math.round(px / (5 * MINUTE_PX)) * 5 * MINUTE_PX
}

const createTopPx = computed(() => {
  if (!creating.value) return 0
  return Math.max(0, snapPx(Math.min(creating.value.startPx, creating.value.currentPx)))
})

const createHeightPx = computed(() => {
  if (!creating.value) return 5 * MINUTE_PX
  return Math.max(5 * MINUTE_PX, snapPx(Math.abs(creating.value.currentPx - creating.value.startPx)))
})

const createDuration = computed(() => Math.round(createHeightPx.value / MINUTE_PX))

const createPreviewStyle = computed(() => ({
  top: `${createTopPx.value}px`,
  height: `${createHeightPx.value}px`,
}))

function onLaneMouseDown(event: MouseEvent, laneKey: string, groupId: number | null) {
  if ((event.target as HTMLElement).closest('.block-tile')) return
  if (event.button !== 0) return
  event.preventDefault()

  const laneEl = event.currentTarget as HTMLElement
  const laneRect = laneEl.getBoundingClientRect()
  // getBoundingClientRect().top already incorporates the scroll offset
  const clientPx = event.clientY - laneRect.top

  creating.value = { laneKey, groupId, startPx: clientPx, currentPx: clientPx + 15 * MINUTE_PX, laneRect }

  const onMove = (e: MouseEvent) => {
    if (!creating.value) return
    // Refresh rect each frame to remain accurate even if user scrolls during drag
    const laneEl = document.querySelector<HTMLElement>(`.lane-col[data-group-id="${creating.value.laneKey}"]`)
    const freshTop = laneEl ? laneEl.getBoundingClientRect().top : creating.value.laneRect.top
    const newPx = e.clientY - freshTop
    creating.value = { ...creating.value, currentPx: Math.max(creating.value.startPx + 5 * MINUTE_PX, newPx) }
  }

  const onUp = async () => {
    document.removeEventListener('mousemove', onMove)
    if (!creating.value) return
    const startOffset = Math.round(createTopPx.value / MINUTE_PX / 5) * 5
    const duration = createDuration.value
    const gId = creating.value.groupId
    creating.value = null

    try {
      await plannerStore.addBlock({
        title: 'Neuer Baustein',
        content: '',
        session: props.sessionId,
        library_block: null,
        duration_minutes: duration,
        start_offset_minutes: Math.max(0, startOffset),
        position_order: blocks.value.length,
        color: '',
        group_ids: gId ? [gId] : [],
      })
      await nextTick()
      const added = blocks.value[blocks.value.length - 1]
      if (added) openEdit(added)
    } catch {
      // error handled by store
    }
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp, { once: true })
}

// ── Drag-from-library-picker ───────────────────────────────────────────────
async function onLaneDrop(event: DragEvent, groupId: number | null) {
  event.preventDefault()
  const blockId = event.dataTransfer?.getData('application/x-library-block-id')
  if (!blockId) return

  const title = event.dataTransfer?.getData('application/x-library-block-title') ?? ''
  const durationStr = event.dataTransfer?.getData('application/x-library-block-duration') ?? '15'
  const duration = parseInt(durationStr) || 15
  const colorStr = event.dataTransfer?.getData('application/x-library-block-color') ?? ''

  const laneEl = event.currentTarget as HTMLElement
  // getBoundingClientRect().top is viewport-relative and already accounts for the
  // scroll offset of .planner-scroll; adding scrollTop again would double-count it.
  const offsetPx = event.clientY - laneEl.getBoundingClientRect().top
  const startOffset = Math.min(DISPLAY_MIN - 5, Math.max(0, Math.round(offsetPx / MINUTE_PX / 5) * 5))

  await plannerStore.addBlock({
    title,
    content: '',
    session: props.sessionId,
    library_block: parseInt(blockId),
    duration_minutes: duration,
    start_offset_minutes: Math.max(0, startOffset),
    position_order: blocks.value.length,
    color: colorStr,
    group_ids: groupId ? [groupId] : [],
  })
  await nextTick()
}

async function addFromLibrary(libraryBlock: LibraryBlockList) {
  await plannerStore.addBlock({
    title: libraryBlock.title,
    content: '',
    session: props.sessionId,
    library_block: libraryBlock.id,
    duration_minutes: libraryBlock.default_duration_minutes ?? 15,
    start_offset_minutes: 0,
    position_order: blocks.value.length,
    color: libraryBlock.color ?? '',
    group_ids: [],
  })
}

// ── Block actions ──────────────────────────────────────────────────────────
// Track drag vs click: set true on first mouse movement, cleared 120 ms after
// drag ends so the synthetic "click" event that follows mouseup is suppressed.
let dragOccurred = false

function openEdit(block: PlannerBlock) {
  if (dragOccurred) return
  editingBlock.value = block
  showEditDialog.value = true
}

function onBlockSaved(_blockId: number) { /* store updated */ }

async function onSessionSaved(_sessionId: number) {
  showSessionSettings.value = false
  await trainingStore.fetchSession(props.sessionId)
}

async function saveAll() {
  saving.value = true
  try { await plannerStore.savePendingMoves() }
  finally { saving.value = false }
}

function goHandout() {
  router.push(`/training/sessions/${props.sessionId}/handout`)
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

// ── Interact.js (drag + resize existing tiles) ────────────────────────────

/** Returns the data-group-id value of the lane column at the given clientX. */
function getLaneKeyAtClientX(clientX: number): string | null {
  const laneEls = Array.from(document.querySelectorAll<HTMLElement>('.lane-col[data-group-id]'))
  for (const el of laneEls) {
    const rect = el.getBoundingClientRect()
    if (clientX >= rect.left && clientX <= rect.right) {
      return el.dataset.groupId ?? 'all'
    }
  }
  return null
}

onMounted(async () => {
  await Promise.all([
    plannerStore.loadBlocks(props.sessionId),
    trainingStore.fetchSession(props.sessionId),
  ])
  await nextTick()
  setupInteract()
})

onBeforeUnmount(() => {
  interact('.block-tile').unset()
})

function setupInteract() {
  interact('.block-tile')
    .draggable({
      listeners: {
        start(event) {
          dragOccurred = false
          const blockId = parseInt(event.target.dataset.blockId)
          const block = blocks.value.find((b) => b.id === blockId)
          // Remember start position for swap detection
          event.target.dataset.originalStart = String(block?.start_offset_minutes ?? 0)
          event.target.dataset.currentTop = event.target.style.top || '0'
          event.target.classList.add('dragging')
          plannerStore.selectBlock(blockId)
        },
        move(event) {
          dragOccurred = true
          const blockId = parseInt(event.target.dataset.blockId)
          const prev = parseFloat(event.target.dataset.currentTop ?? '0')
          const rawTop = Math.max(0, prev + event.dy)
          event.target.dataset.currentTop = String(rawTop)
          // 1-minute snap
          const snapped = Math.round(rawTop / MINUTE_PX) * MINUTE_PX
          event.target.style.top = `${snapped}px`
          plannerStore.stageMove(blockId, { start_offset_minutes: Math.round(snapped / MINUTE_PX) })
          // Track target lane for cross-lane drop
          const laneKey = getLaneKeyAtClientX(event.client.x)
          if (laneKey !== null) event.target.dataset.targetLane = laneKey
        },
        end(event) {
          event.target.classList.remove('dragging')
          if (dragOccurred) {
            // Swap detection runs after the reactive update settles
            const blockId = parseInt(event.target.dataset.blockId)
            const originalStart = parseInt(event.target.dataset.originalStart ?? '0')
            // Apply cross-lane change if block was dragged to a different lane
            const targetLaneKey = event.target.dataset.targetLane
            if (targetLaneKey !== undefined) {
              const block = blocks.value.find((b) => b.id === blockId)
              if (block) {
                const currentLaneKey = block.allGroups ? 'all' : String(block.groupIds[0] ?? 'all')
                if (targetLaneKey !== currentLaneKey) {
                  const newGroups = targetLaneKey === 'all' ? [] : [parseInt(targetLaneKey)]
                  plannerStore.stageMove(blockId, { groups: newGroups })
                }
              }
            }
            swapIfOverlapping(blockId, originalStart)
            // Keep the flag true long enough to swallow the synthetic click event
            setTimeout(() => { dragOccurred = false }, 150)
          }
          delete event.target.dataset.currentTop
          delete event.target.dataset.originalStart
          delete event.target.dataset.targetLane
        },
      },
    })
    .resizable({
      edges: { bottom: '.resize-handle' },
      listeners: {
        start(event) {
          dragOccurred = false
          // Capture initial height to avoid fighting Vue's reactive :style binding
          event.target.dataset.currentHeight = String(event.target.offsetHeight)
        },
        move(event) {
          dragOccurred = true
          const blockId = parseInt(event.target.dataset.blockId)
          // Accumulate delta manually (event.deltaRect.bottom = change in bottom edge)
          const prev = parseFloat(event.target.dataset.currentHeight ?? String(MINUTE_PX * 15))
          const rawHeight = Math.max(MINUTE_PX, prev + event.deltaRect.bottom)
          event.target.dataset.currentHeight = String(rawHeight)
          // Snap to 1-minute increments
          const snapped = Math.max(MINUTE_PX, Math.round(rawHeight / MINUTE_PX) * MINUTE_PX)
          event.target.style.height = `${snapped}px`
          plannerStore.stageMove(blockId, { duration_minutes: Math.round(snapped / MINUTE_PX) })
        },
        end(event) {
          if (dragOccurred) setTimeout(() => { dragOccurred = false }, 150)
          delete event.target.dataset.currentHeight
        },
      },
    })
}

/**
 * After a drag ends: if the dragged block overlaps another block in the same lane
 * by more than 40% of the smaller block’s duration, swap them.
 */
function swapIfOverlapping(draggedId: number, draggedOriginalStart: number) {
  const dragged = blocks.value.find((b) => b.id === draggedId)
  if (!dragged) return

  const dStart = dragged.start_offset_minutes ?? 0
  const dEnd = dStart + dragged.duration_minutes

  // Find which lane the dragged block lives in
  const lane = visibleLanes.value.find((l) => l.blocks.some((b) => b.id === draggedId))
  if (!lane) return

  let bestOverlap = 0
  let bestBlock: (typeof lane.blocks)[number] | null = null

  for (const other of lane.blocks) {
    if (other.id === draggedId) continue
    const oStart = other.start_offset_minutes ?? 0
    const oEnd = oStart + other.duration_minutes
    const overlap = Math.max(0, Math.min(dEnd, oEnd) - Math.max(dStart, oStart))
    if (overlap > bestOverlap) {
      bestOverlap = overlap
      bestBlock = other
    }
  }

  if (!bestBlock) return
  const smaller = Math.min(dragged.duration_minutes, bestBlock.duration_minutes)
  if (bestOverlap < smaller * 0.4) return

  // Swap: send the displaced block to where the dragged block started
  plannerStore.stageMove(bestBlock.id, { start_offset_minutes: draggedOriginalStart })
  const otherEl = document.querySelector(`[data-block-id="${bestBlock.id}"]`) as HTMLElement | null
  if (otherEl) otherEl.style.top = `${draggedOriginalStart * MINUTE_PX}px`
}
</script>

<style scoped>
/* ── Outer shell ──────────────────────────────────────────────────────── */
.swimlane-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-ground);
  overflow: hidden;
}

/* ── Topbar ───────────────────────────────────────────────────────────── */
.editor-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 1rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
  flex-shrink: 0;
  gap: 1rem;
  min-height: 52px;
}
.session-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.session-title { font-size: 1rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-meta { font-size: 0.8rem; color: var(--text-color-secondary); }
.topbar-actions { display: flex; gap: 0.5rem; flex-shrink: 0; }

/* ── Planner container ────────────────────────────────────────────────── */
.planner-container {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

/* ── Scroll area ──────────────────────────────────────────────────────── */
.planner-scroll {
  flex: 1;
  overflow: auto;
  position: relative;
}

/* ── Sticky header row ────────────────────────────────────────────────── */
.header-row {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  background: var(--surface-card);
  border-bottom: 2px solid var(--primary-color);
  height: 40px;
}

.time-corner {
  width: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-color-secondary);
  border-right: 1px solid var(--surface-border);
  position: sticky;
  left: 0;
  background: var(--surface-card);
  z-index: 11;
}

.lane-header-cell {
  min-width: 200px;
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 0.75rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-right: 1px solid var(--surface-border);
  color: var(--text-color);
  background: var(--surface-card);
}
.lane-header-cell:last-child { border-right: none; }

/* ── Loading ──────────────────────────────────────────────────────────── */
.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  height: 300px;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

/* ── Grid body ────────────────────────────────────────────────────────── */
.grid-body {
  display: flex;
  position: relative;
}

/* ── Time ruler ───────────────────────────────────────────────────────── */
.time-ruler {
  width: 64px;
  flex-shrink: 0;
  position: sticky;
  left: 0;
  z-index: 5;
  background: var(--surface-50);
  border-right: 2px solid var(--surface-200);
}

.ruler-label {
  position: absolute;
  right: 6px;
  transform: translateY(-50%);
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  white-space: nowrap;
  pointer-events: none;
  z-index: 1;
}

.ruler-hline {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--surface-200);
}
.ruler-hline--hour { background: var(--surface-400); height: 2px; }
.ruler-hline--quarter { background: var(--surface-300); }

/* ── Lane columns ─────────────────────────────────────────────────────── */
.lanes-wrap {
  flex: 1;
  display: flex;
}

.lane-col {
  flex: 1;
  min-width: 200px;
  position: relative;
  border-right: 1px solid var(--surface-border);
  cursor: crosshair;
  background: var(--surface-ground);
}
.lane-col:last-child { border-right: none; }

/* ── Grid lines ───────────────────────────────────────────────────────── */
.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  pointer-events: none;
}
.grid-line--quarter { background: var(--surface-100); }
.grid-line--hour { background: var(--surface-200); height: 2px; }

/* ── Drag-to-create preview ───────────────────────────────────────────── */
.create-preview {
  position: absolute;
  left: 4px;
  right: 4px;
  background: color-mix(in srgb, var(--primary-color) 12%, transparent);
  border: 2px dashed var(--primary-color);
  border-radius: 6px;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 4;
}
.create-preview__label {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--primary-color);
  text-align: center;
  padding: 0 0.25rem;
}

/* ── Library panel ────────────────────────────────────────────────────── */
.library-panel {
  width: 280px;
  flex-shrink: 0;
  overflow: hidden;
  border-left: 1px solid var(--surface-border);
  background: var(--surface-card);
}

/* ── Slide transition ─────────────────────────────────────────────────── */
.slide-panel-enter-active,
.slide-panel-leave-active { transition: width 0.2s ease; overflow: hidden; }
.slide-panel-enter-from,
.slide-panel-leave-to { width: 0; }
</style>
