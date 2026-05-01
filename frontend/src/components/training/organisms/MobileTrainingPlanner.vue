<template>
  <div class="mobile-planner">

    <!-- ── Session header ──────────────────────────────────────────── -->
    <div class="mobile-header">
      <div class="header-main">
        <h1 class="session-title">{{ session?.title ?? 'Trainingsplanung' }}</h1>
        <div v-if="session" class="session-meta">
          <span class="meta-item">
            <i class="pi pi-calendar" />
            {{ formatDate(session.date) }}
          </span>
          <span v-if="session.start_time" class="meta-item">
            <i class="pi pi-clock" />
            {{ session.start_time }} – {{ session.end_time }} Uhr
          </span>
          <span v-if="session.location" class="meta-item">
            <i class="pi pi-map-marker" />
            {{ session.location }}
          </span>
        </div>
      </div>
      <div class="header-buttons">
        <Button
          icon="pi pi-file-pdf"
          label="Handout"
          size="small"
          severity="secondary"
          outlined
          @click="router.push(`/training/sessions/${sessionId}/handout`)"
        />
        <Button
          icon="pi pi-arrow-left"
          label="Zurück"
          size="small"
          severity="secondary"
          outlined
          @click="router.push('/training')"
        />
      </div>
    </div>

    <!-- ── Loading ─────────────────────────────────────────────────── -->
    <div v-if="plannerStore.loading || trainingStore.loading" class="loading-state">
      <i class="pi pi-spin pi-spinner" />
      <span>Lade Trainingsplan…</span>
    </div>

    <!-- ── No blocks ───────────────────────────────────────────────── -->
    <div v-else-if="plannerStore.blocks.length === 0" class="empty-state">
      <i class="pi pi-calendar-times" style="font-size: 2.5rem; color: var(--p-text-muted-color)" />
      <p>Noch keine Bausteine geplant.</p>
    </div>

    <!-- ── Group tabs ──────────────────────────────────────────────── -->
    <div v-else class="lanes-section">
      <!-- Tab bar -->
      <div class="lane-tabs" ref="tabBarRef">
        <button
          v-for="(lane, index) in visibleLanes"
          :key="lane.key"
          class="lane-tab"
          :class="{ active: activeTab === index }"
          @click="activeTab = index"
        >
          {{ lane.label }}
          <span class="tab-count">{{ lane.blocks.length }}</span>
        </button>
      </div>

      <!-- Active lane blocks -->
      <div class="lane-content">
        <template v-if="activeLane">
          <div v-if="activeLane.blocks.length === 0" class="lane-empty">
            <i class="pi pi-inbox" />
            <span>Keine Bausteine für diese Gruppe</span>
          </div>

          <button
            v-for="block in activeLane.blocks"
            :key="block.id"
            class="block-card"
            :style="blockCardStyle(block)"
            @click="selectedBlock = block"
          >
            <div class="card-time">
              {{ blockStartTime(block) }} – {{ blockEndTime(block) }}
            </div>
            <div class="card-body">
              <div class="card-title">{{ block.title }}</div>
              <div class="card-meta">
                <span class="card-duration">
                  <i class="pi pi-clock" />
                  {{ block.duration_minutes }} min
                </span>
                <span v-if="block.content || block.media?.length" class="card-hint">
                  <i class="pi pi-chevron-right" />
                  Details
                </span>
              </div>
            </div>
          </button>
        </template>
      </div>
    </div>
  </div>

  <!-- Block detail bottom sheet -->
  <MobileBlockDetailSheet
    :block="selectedBlock"
    :session-start-min="sessionStartMin"
    @close="selectedBlock = null"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import MobileBlockDetailSheet from '@/components/training/molecules/MobileBlockDetailSheet.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'
import { useTrainingStore } from '@/stores/training'
import type { PlannerBlock, TrainingSessionDetail } from '@/types/training'

interface Props {
  sessionId: number
}
const props = defineProps<Props>()
const router = useRouter()

const plannerStore = useTrainingPlannerStore()
const trainingStore = useTrainingStore()

const activeTab = ref(0)
const tabBarRef = ref<HTMLElement | null>(null)
const selectedBlock = ref<PlannerBlock | null>(null)

// ── Session & blocks ────────────────────────────────────────────────────────
const session = computed(() => trainingStore.currentSession as TrainingSessionDetail | null)

const sessionStartMin = computed(() => {
  const t = session.value?.start_time
  if (!t) return 8 * 60
  const parts = t.split(':')
  return Number(parts[0] ?? 8) * 60 + Number(parts[1] ?? 0)
})

// ── Visible lanes (same logic as SwimlaneEditor) ────────────────────────────
const visibleLanes = computed(() => {
  const groupMap = new Map<number, string>()
  if (session.value?.groups) {
    for (const g of session.value.groups) groupMap.set(g.id, g.name)
  }
  for (const b of plannerStore.blocks) {
    for (const gId of b.groupIds) {
      if (!groupMap.has(gId)) groupMap.set(gId, `Gruppe ${gId}`)
    }
  }

  const result: { key: string; groupId: number | null; label: string; blocks: PlannerBlock[] }[] = [
    {
      key: 'all',
      groupId: null,
      label: 'Alle Gruppen',
      blocks: [...plannerStore.blocks.filter((b) => b.allGroups)].sort(
        (a, b) => a.start_offset_minutes - b.start_offset_minutes,
      ),
    },
  ]

  for (const [gId, gName] of groupMap) {
    result.push({
      key: String(gId),
      groupId: gId,
      label: gName,
      blocks: [...plannerStore.blocks.filter((b) => !b.allGroups && b.groupIds.includes(gId))].sort(
        (a, b) => a.start_offset_minutes - b.start_offset_minutes,
      ),
    })
  }

  return result
})

const activeLane = computed(() => visibleLanes.value[activeTab.value] ?? null)

// ── Helpers ─────────────────────────────────────────────────────────────────
function absMinToTime(abs: number): string {
  const hh = Math.floor(abs / 60) % 24
  const mm = abs % 60
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

function blockStartTime(block: PlannerBlock): string {
  return absMinToTime(sessionStartMin.value + block.start_offset_minutes)
}

function blockEndTime(block: PlannerBlock): string {
  return absMinToTime(sessionStartMin.value + block.start_offset_minutes + block.duration_minutes)
}

function blockCardStyle(block: PlannerBlock) {
  if (!block.color) return {}
  return {
    borderLeftColor: block.color,
    backgroundColor: `${block.color}18`,
  }
}


function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

// ── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    plannerStore.loadBlocks(props.sessionId),
    trainingStore.fetchSession(props.sessionId),
  ])
})
</script>

<style scoped>
/* ── Outer shell ──────────────────────────────────────────────────────────── */
.mobile-planner {
  min-height: 100svh;
  background: var(--p-content-background);
  display: flex;
  flex-direction: column;
  font-size: 0.95rem;
}

/* ── Header ───────────────────────────────────────────────────────────────── */
.mobile-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  flex-shrink: 0;
}

.header-main { flex: 1; min-width: 0; }

.session-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
  line-height: 1.25;
}

.session-meta {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.meta-item .pi {
  font-size: 0.75rem;
  flex-shrink: 0;
}

/* ── Loading / empty states ───────────────────────────────────────────────── */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 4rem 1rem;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  flex: 1;
}

.loading-state .pi { font-size: 1.8rem; }

/* ── Lane tabs ────────────────────────────────────────────────────────────── */
.lanes-section {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.lane-tabs {
  display: flex;
  overflow-x: auto;
  border-bottom: 2px solid var(--p-content-border-color);
  background: var(--p-content-background);
  position: sticky;
  top: 0;
  z-index: 9;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.lane-tabs::-webkit-scrollbar { display: none; }

.lane-tab {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.65rem 1rem;
  font-size: 0.85rem;
  font-weight: 500;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  color: var(--p-text-muted-color);
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.lane-tab.active {
  color: var(--p-primary-color);
  border-bottom-color: var(--p-primary-color);
  font-weight: 600;
}

.tab-count {
  background: var(--p-content-border-color);
  color: var(--p-text-muted-color);
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 0.05rem 0.42rem;
  line-height: 1.6;
}

.lane-tab.active .tab-count {
  background: color-mix(in srgb, var(--p-primary-color) 20%, transparent);
  color: var(--p-primary-color);
}

/* ── Lane content (block cards) ───────────────────────────────────────────── */
.lane-content {
  padding: 0.75rem 1rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.lane-empty {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
  padding: 3rem 1rem;
  color: var(--p-text-muted-color);
  font-size: 0.88rem;
}

/* ── Block card ───────────────────────────────────────────────────────────── */
.block-card {
  display: flex;
  gap: 0.75rem;
  background: var(--p-surface-card, var(--p-content-background));
  border: 1px solid var(--p-content-border-color);
  border-left: 4px solid var(--p-primary-color);
  border-radius: 8px;
  padding: 0.75rem;
  min-height: 60px;
  width: 100%;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background 0.1s;
}
.block-card:active {
  background: var(--p-content-hover-background, color-mix(in srgb, var(--p-content-border-color) 30%, var(--p-content-background)));
}

.card-time {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  padding-top: 0.1rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--p-text-muted-color);
  white-space: nowrap;
  min-width: 88px;
  font-variant-numeric: tabular-nums;
}

.card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.3;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.card-duration {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.card-duration .pi {
  font-size: 0.7rem;
}

.card-hint {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.72rem;
  color: var(--p-primary-color);
  font-weight: 600;
}
.card-hint .pi { font-size: 0.65rem; }
</style>
