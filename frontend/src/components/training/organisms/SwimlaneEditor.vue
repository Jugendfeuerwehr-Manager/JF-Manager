<template>
  <div class="swimlane-editor" @keydown="onEditorKeydown">

    <!-- ── Header (UX-09: shared workspace header, one main action, the rest by width) ── -->
    <WorkspaceHeader
      ref="headerRef"
      class="planner-head"
      :class="`planner-head--${tier}`"
      :title="session?.title ?? 'Trainingsplanung'"
      back-to="/training"
      back-label="Ausbildung"
      :eyebrow="eyebrow"
    >
      <template v-if="session" #meta>
        <TrainingStatusBadge :status="session.status" />
        <span>Version {{ session.revision }}</span>
        <router-link v-if="session.linked_service_id" :to="`/servicebook/${session.linked_service_id}/attendance`">Dienst und Anwesenheit</router-link>
        <span v-if="session.location || laneSummary">{{ [laneSummary, session.location].filter(Boolean).join(' · ') }}</span>
      </template>
      <template #status>
        <span class="save-hint" :class="{ 'save-hint--dirty': isDirty, 'save-hint--error': saveFailed }" role="status">
          <template v-if="plannerStore.loading">Plan lädt …</template>
          <template v-else-if="plannerStore.saving">Speichert …</template>
          <template v-else-if="saveFailed || plannerStore.error"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>Nicht gespeichert</template>
          <template v-else-if="isDirty"><i class="pi pi-pencil" aria-hidden="true"></i>{{ compactHeader ? 'Ungespeichert' : pendingLabel }}</template>
          <template v-else><i class="pi pi-check" aria-hidden="true"></i>{{ compactHeader ? 'Gespeichert' : 'Alles gespeichert' }}</template>
        </span>
      </template>
      <template #actions>
        <Button
          v-for="action in headerActions.inline"
          :key="action.key"
          :icon="action.icon"
          :label="action.iconOnly ? undefined : action.label"
          :aria-label="action.iconOnly ? action.label : undefined"
          :aria-expanded="action.expanded"
          :aria-pressed="action.pressed"
          severity="secondary"
          :text="action.text"
          :outlined="action.outlined"
          :disabled="action.disabled"
          v-tooltip.bottom="action.hint ?? (action.iconOnly ? action.label : undefined)"
          @click="action.command()"
        />
        <Button
          v-if="headerActions.menu.length"
          icon="pi pi-ellipsis-v"
          severity="secondary"
          text
          aria-label="Weitere Aktionen"
          aria-haspopup="menu"
          aria-controls="planner-more-actions"
          v-tooltip.bottom="'Weitere Aktionen'"
          :disabled="plannerStore.loading"
          @click="moreMenu?.toggle($event)"
        />
        <Menu id="planner-more-actions" ref="moreMenu" :model="moreItems" popup />
        <Button
          v-if="canManage"
          icon="pi pi-save"
          label="Speichern"
          :loading="plannerStore.saving || saving"
          :disabled="!isDirty || plannerStore.loading || showEditDialog || showSessionSettings || showPlanAction || showRotation"
          @click="saveAll"
        />
      </template>
    </WorkspaceHeader>

    <div v-if="plannerStore.error" role="alert">
      <p>{{ plannerStore.error }}</p>
      <Button v-if="!session" label="Erneut laden" severity="secondary" @click="plannerStore.loadBlocks(sessionId).catch(() => {})" />
    </div>
    <details v-if="plannerStore.conflict" class="plan-conflict" open>
      <summary>Serverstand vergleichen · Version {{ plannerStore.conflict.revision }}</summary>
      <p>Dein Entwurf bleibt im Planer erhalten. Der Server enthält:</p>
      <p>{{ plannerStore.conflict.title }} · {{ plannerStore.conflict.date }} · {{ formatTimeRange(plannerStore.conflict.start_time, plannerStore.conflict.end_time) }}</p>
      <ul>
        <li v-for="block in plannerStore.conflict.blocks" :key="block.id">
          {{ block.title }} · ab Minute {{ block.start_offset_minutes }} · {{ block.duration_minutes }} Minuten
        </li>
      </ul>
      <Button label="Serverstand laden und Entwurf verwerfen" severity="secondary" @click="discardForServerVersion" />
    </details>

    <PlanWarningsPanel v-if="canManage && session" @focus-block="focusBlock" />
    <PublishJustificationDialog
      v-model:visible="showJustification"
      :warnings="plannerStore.warnings.map((w) => w.message)"
      :initial="session?.publish_justification"
      @confirm="(text) => plannerStore.stageSession({ status: 'published', publish_justification: text })"
    />

    <!-- ── Main planner ────────────────────────────────────────────── -->
    <div class="planner-container" :inert="plannerStore.saving || plannerStore.loading">

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
        <div v-if="plannerStore.loading" class="loading-overlay" role="status">
          <i class="pi pi-spin pi-spinner" style="font-size: 2rem; color: var(--jf-color-primary)" aria-hidden="true"></i>
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

              <!-- "All Groups" ghost hatching: shown in every group-specific lane -->
              <template v-if="lane.groupId !== null">
                <div
                  v-for="allBlock in allGroupsBlocks"
                  :key="`ghost-${allBlock.id}`"
                  class="all-groups-ghost"
                  :style="{
                    top: `${(allBlock.start_offset_minutes ?? 0) * MINUTE_PX}px`,
                    height: `${allBlock.duration_minutes * MINUTE_PX}px`,
                  }"
                  v-tooltip.left="`'${allBlock.title}' (Alle Gruppen)`"
                />
              </template>

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
                :read-only="!canManage"
                :minute-height="MINUTE_PX"
                :selected="selectedBlockId === block.id"
                @click="openEdit(block)"
                @edit="openEdit(block)"
                @move="onKeyboardMove"
                @remove="canManage && plannerStore.removeBlock($event)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Library picker sidebar -->
      <Transition name="slide-panel">
        <div v-if="canManage && showLibraryPicker" class="library-panel" :style="{ '--library-width': `${libraryWidth}px` }">
          <!-- UX-09: drag, arrow keys or double-click (default) change the width; remembered per user -->
          <div
            class="library-resizer"
            role="separator"
            tabindex="0"
            aria-orientation="vertical"
            aria-controls="planner-library"
            aria-label="Breite der Bibliothek"
            :aria-valuenow="libraryWidth"
            :aria-valuemin="libraryMinWidth"
            :aria-valuemax="libraryMaxWidth"
            :aria-valuetext="`${libraryWidth} Pixel breit`"
            v-tooltip.left="'Breite ändern: ziehen oder Pfeiltasten, Doppelklick setzt zurück'"
            @pointerdown="startLibraryResize"
            @keydown="onLibraryResizeKey"
            @dblclick="resetLibraryWidth"
          ></div>
          <LibraryBlockPicker id="planner-library" @pick="addFromLibrary" @close="showLibraryPicker = false" />
        </div>
      </Transition>
    </div>

    <MobileBlockDetailSheet v-if="!canManage" :block="readingBlock" :session-start-min="sessionStartMin" @close="readingBlock = null" />
    <PlanActionDialog v-model:visible="showPlanAction" :duration="sessionDuration" />
    <RotationDialog v-if="canManage" v-model:visible="showRotation" :duration="sessionDuration" />
    <DebriefDialog v-if="canManage && session && showDebrief" v-model:visible="showDebrief" :session="session" @saved="onDebriefSaved" />
    <SessionCopyDialog v-if="canManage" v-model:visible="showCopy" :mode="copyMode" :session="session" @copied="onCopied" @saved="onTemplateSaved" />
    <ParticipationDialog v-if="session" v-model:visible="showParticipation" :session-id="session.id" :can-manage="canManage" />
    <SeriesDialog v-if="canManage" v-model:visible="showSeries" :session-id="session?.id ?? null" :can-propagate="!!session?.series_uuid" />

    <!-- Session settings dialog -->
    <Dialog
      v-model:visible="showSessionSettings"
      header="Training bearbeiten"
      :style="{ width: '640px', maxWidth: 'calc(100vw - 24px)' }"
      modal
    >
      <TrainingSessionForm
        v-if="session"
        :initial-data="(session as TrainingSessionDetail)"
        draft-only
        @draft="onSessionDraft"
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
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { useClientConfiguration } from '@/composables/useClientConfiguration'
const { configuration, refresh: refreshDefaults } = useClientConfiguration()
onMounted(() => { void refreshDefaults().catch(() => { /* Keep safe fallback duration. */ }) })
import Button from 'primevue/button'
import TrainingStatusBadge from '../atoms/TrainingStatusBadge.vue'
import Dialog from 'primevue/dialog'
import TrainingBlockTile from '../molecules/TrainingBlockTile.vue'
import LibraryBlockPicker from '../molecules/LibraryBlockPicker.vue'
import MobileBlockDetailSheet from '../molecules/MobileBlockDetailSheet.vue'
import BlockEditDialog from '../molecules/BlockEditDialog.vue'
import PlanActionDialog from '../molecules/PlanActionDialog.vue'
import SeriesDialog from '../molecules/SeriesDialog.vue'
import RotationDialog from '../molecules/RotationDialog.vue'
import DebriefDialog from '../molecules/DebriefDialog.vue'
import SessionCopyDialog from '../molecules/SessionCopyDialog.vue'
import PlanWarningsPanel from '../molecules/PlanWarningsPanel.vue'
import PublishJustificationDialog from '../molecules/PublishJustificationDialog.vue'
import ParticipationDialog from '@/components/participation/ParticipationDialog.vue'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import { useToast } from 'primevue/usetoast'
import TrainingSessionForm from '../molecules/TrainingSessionForm.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'
import type { PlannerBlock, LibraryBlockList, TrainingSessionDetail, TrainingSessionCreate, GroupMini, TrainingBlockMove, TrainingStatus, TrainingDebrief } from '@/types/training'
import interact from 'interactjs'
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import { useElementWidth } from '@/composables/useElementWidth'
import { headerTier, menuLabel, splitHeaderActions, type HeaderAction } from '../utils/headerActions'
import { usePlannerLibraryPanel } from '@/composables/usePlannerLibraryPanel'
import { useAuthStore } from '@/stores/auth'

interface Props {
  sessionId: number
}
const props = defineProps<Props>()
const router = useRouter()

const plannerStore = useTrainingPlannerStore()

// ── Constants ──────────────────────────────────────────────────────────────
const MINUTE_PX = 4      // px per minute → 240 min × 4 = 960 px total
const sessionDuration = computed(() => {
  const minutes = (value: string) => value.split(':').reduce((sum, part, index) => sum + Number(part) * [60, 1, 1 / 60][index]!, 0)
  const s = plannerStore.session
  return s ? Math.max(1, Math.floor(minutes(s.end_time) - minutes(s.start_time))) : 240
})

// ── Refs ───────────────────────────────────────────────────────────────────
const plannerScroll = ref<HTMLElement | null>(null)
const auth = useAuthStore()
const {
  width: libraryWidth,
  open: libraryOpen,
  setOpen: setLibraryOpen,
  reset: resetLibraryWidth,
  onSeparatorKey: onLibraryResizeKey,
  startDrag: startLibraryResize,
  minWidth: libraryMinWidth,
  maxWidth: libraryMaxWidth,
} = usePlannerLibraryPanel(computed(() => auth.user?.id))
const showLibraryPicker = computed({
  get: () => libraryOpen.value,
  set: (value: boolean) => setLibraryOpen(value),
})
const showEditDialog = ref(false)
const showSessionSettings = ref(false)
const showPlanAction = ref(false)
const showSeries = ref(false)
const showRotation = ref(false)
const showDebrief = ref(false)
const showParticipation = ref(false)
// Follow-up once the exercise has begun (device time); the server checks again.
const canDebrief = computed(() => {
  const s = plannerStore.session
  if (!s || (s.status !== 'published' && s.status !== 'completed')) return false
  return new Date(`${s.date}T${s.start_time}`) <= new Date()
})

async function onDebriefSaved(debrief: TrainingDebrief) {
  toast.add({ severity: 'success', summary: 'Nachbereitung gespeichert', life: 3000 })
  // Completing changes status and plan version: show the server state.
  if (plannerStore.session && debrief.session_status !== plannerStore.session.status) await plannerStore.loadBlocks(plannerStore.session.id)
}
const showCopy = ref(false)
const showJustification = ref(false)
const copyMode = ref<'copy' | 'template'>('copy')
const moreMenu = ref<InstanceType<typeof Menu> | null>(null)
const toast = useToast()
// ── Header actions (UX-09) ─────────────────────────────────────────────────
// "Speichern" is the only main action. Secondary actions appear as buttons as the
// header gets wider; everything else is in the "Weitere Aktionen" menu, so a phone
// shows status, "Speichern" and the menu in one row.
const headerRef = ref<{ $el: HTMLElement } | null>(null)
const headerWidth = useElementWidth(computed(() => headerRef.value?.$el ?? null))
const tier = computed(() => headerTier(headerWidth.value))
const compactHeader = computed(() => tier.value === 'sm')
const eyebrow = computed(() => {
  const s = session.value
  if (!s?.date) return undefined
  return [formatDate(s.date), s.start_time ? formatTimeRange(s.start_time, s.end_time) : ''].filter(Boolean).join(' · ')
})

const dialogOpen = computed(() => showEditDialog.value || showSessionSettings.value || showPlanAction.value || showRotation.value)
const busy = computed(() => plannerStore.saving || plannerStore.loading)

const allHeaderActions = computed<HeaderAction[]>(() => {
  const s = session.value
  const manage = canManage.value
  const runnable = !!s && (s.status === 'published' || s.status === 'completed') && blocks.value.length > 0
  return [
    { key: 'undo', label: 'Rückgängig', icon: 'pi pi-undo', tier: 'md', iconOnly: true, text: true, visible: manage,
      disabled: !plannerStore.canUndo || dialogOpen.value, command: () => plannerStore.undo() },
    { key: 'redo', label: 'Wiederholen', icon: 'pi pi-refresh', tier: 'md', iconOnly: true, text: true, visible: manage,
      disabled: !plannerStore.canRedo || dialogOpen.value, command: () => plannerStore.redo() },
    { key: 'library', label: showLibraryPicker.value ? 'Bibliothek schließen' : 'Bibliothek', icon: showLibraryPicker.value ? 'pi pi-times' : 'pi pi-book',
      tier: 'md', outlined: !showLibraryPicker.value, expanded: showLibraryPicker.value, visible: manage, disabled: busy.value,
      command: () => { showLibraryPicker.value = !showLibraryPicker.value } },
    { key: 'block', label: 'Baustein', icon: 'pi pi-plus', tier: 'lg', visible: manage, disabled: busy.value, command: () => { void createBlock() } },
    { key: 'publish', label: 'Veröffentlichen', icon: 'pi pi-send', tier: 'lg', visible: manage && (s?.status === 'draft' || s?.status === 'cancelled'),
      disabled: busy.value, command: () => { void stageStatus('published') } },
    { key: 'complete', label: 'Abschließen', icon: 'pi pi-check-circle', tier: 'lg', visible: manage && s?.status === 'published' && !!s.linked_service_id,
      disabled: busy.value, command: () => { void stageStatus('completed') } },
    { key: 'run', label: 'Durchführen', icon: 'pi pi-play', tier: manage ? 'xl' : 'md', visible: runnable,
      hint: isDirty.value ? 'Zeigt den gespeicherten Stand' : 'Ablauf vor Ort auf dem Telefon',
      command: () => { if (s) void router.push({ name: 'training-run', params: { id: s.id } }) } },
    { key: 'debrief', label: 'Nachbereiten', icon: 'pi pi-comment', tier: 'xl', visible: manage && canDebrief.value,
      disabled: isDirty.value || plannerStore.saving, disabledReason: 'zuerst speichern',
      hint: isDirty.value ? 'Zuerst speichern' : 'Tatsächliche Zeit, Reflexion und Verbesserungen', command: () => { showDebrief.value = true } },
    { key: 'rotation', label: 'Rotation', icon: 'pi pi-th-large', tier: 'xl', visible: manage, disabled: busy.value, command: () => { showRotation.value = true } },
    { key: 'plan-action', label: 'Planaktion', icon: 'pi pi-arrows-h', tier: 'xl', visible: manage, disabled: busy.value || blocks.value.length < 1,
      command: () => { showPlanAction.value = true } },
    { key: 'participation', label: 'Teilnahme', icon: 'pi pi-users', tier: manage ? 'xl' : 'lg', text: true, visible: !!s && (manage || s.status !== 'draft'),
      hint: 'Anmeldemodus, Fristen, Voraussetzungen und Meldungen', command: () => { showParticipation.value = true } },
    { key: 'handout', label: 'Handout', icon: 'pi pi-file-pdf', tier: manage ? 'menu' : 'lg', text: true, visible: true, command: goHandout },
    { key: 'series', label: 'Serie', icon: 'pi pi-sync', tier: 'menu', visible: manage && isSeries.value,
      disabled: busy.value || isDirty.value, disabledReason: 'zuerst speichern',
      hint: 'Serientermine ergänzen oder diesen Stand auf folgende übertragen', command: () => { showSeries.value = true } },
    { key: 'settings', label: 'Einstellungen der Übung', icon: 'pi pi-cog', tier: 'menu', visible: manage, disabled: busy.value,
      command: () => { showSessionSettings.value = true } },
    // Copies and templates use the saved state, never unsaved local changes.
    { key: 'copy', label: 'Auf anderes Datum kopieren', icon: 'pi pi-copy', tier: 'menu', visible: manage,
      disabled: isDirty.value || busy.value, disabledReason: 'zuerst speichern', command: () => openCopy('copy') },
    { key: 'template', label: 'Als Vorlage speichern', icon: 'pi pi-bookmark', tier: 'menu', visible: manage,
      disabled: isDirty.value || busy.value, disabledReason: 'zuerst speichern', command: () => openCopy('template') },
    // Cancelling is never a button next to "Speichern".
    { key: 'cancel', label: 'Absagen', icon: 'pi pi-ban', tier: 'menu', visible: manage && !!s && s.status !== 'cancelled' && s.status !== 'completed',
      disabled: busy.value, command: () => { void stageStatus('cancelled') } },
  ]
})

const headerActions = computed(() => splitHeaderActions(allHeaderActions.value, headerWidth.value))
const moreItems = computed<MenuItem[]>(() => headerActions.value.menu.map((action) => ({
  key: action.key,
  label: menuLabel(action),
  icon: action.icon,
  disabled: action.disabled,
  command: () => action.command(),
})))
function openCopy(mode: 'copy' | 'template') {
  copyMode.value = mode
  showCopy.value = true
}
function onCopied(copy: TrainingSessionDetail) {
  router.push(`/training/sessions/${copy.id}/plan`)
}
function onTemplateSaved() {
  toast.add({ severity: 'success', summary: 'Vorlage gespeichert', detail: 'Sie steht im Kalender unter „Vorlagen“ bereit.', life: 4000 })
}
const editingBlock = ref<PlannerBlock | null>(null)
const saving = ref(false)
const saveFailed = ref(false)

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
const isSeries = computed(() => !!session.value && (!!session.value.recurrence_rule || !!session.value.series_uuid || session.value.series_parent !== null))
const session = computed(() => plannerStore.session)
const canManage = computed(() => session.value?.can_manage_plan !== false)
const readingBlock = ref<PlannerBlock | null>(null)
const totalHeightPx = computed(() => sessionDuration.value * MINUTE_PX)

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
  for (let offset = 0; offset <= sessionDuration.value; offset += 5) {
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

/** Blocks that belong to the "All Groups" lane — used to render ghost hatching. */
const allGroupsBlocks = computed(() => blocks.value.filter((b) => b.allGroups))

// ── Drag-to-create helpers ─────────────────────────────────────────────────
function snapPx(px: number): number {
  return Math.round(px / (5 * MINUTE_PX)) * 5 * MINUTE_PX
}

const createTopPx = computed(() => {
  if (!creating.value) return 0
  return Math.min((sessionDuration.value - 1) * MINUTE_PX, Math.max(0, snapPx(Math.min(creating.value.startPx, creating.value.currentPx))))
})

const createHeightPx = computed(() => {
  if (!creating.value) return 5 * MINUTE_PX
  return Math.min(totalHeightPx.value - createTopPx.value, Math.max(5 * MINUTE_PX, snapPx(Math.abs(creating.value.currentPx - creating.value.startPx))))
})

const createDuration = computed(() => Math.round(createHeightPx.value / MINUTE_PX))

const createPreviewStyle = computed(() => ({
  top: `${createTopPx.value}px`,
  height: `${createHeightPx.value}px`,
}))

function onLaneMouseDown(event: MouseEvent, laneKey: string, groupId: number | null) {
  if (!canManage.value) return
  if ((event.target as HTMLElement).closest('.block-tile')) return
  if (event.button !== 0 || plannerStore.saving || plannerStore.loading) return
  event.preventDefault()

  const laneEl = event.currentTarget as HTMLElement
  const initialLaneTop = laneEl.getBoundingClientRect().top
  const startClientY = event.clientY
  // Drag is only "real" after the pointer moves at least 5 px
  let hasDragged = false

  const onMove = (e: MouseEvent) => {
    if (!hasDragged) {
      if (Math.abs(e.clientY - startClientY) < 5) return
      hasDragged = true
    }
    // Re-fetch the lane top so the preview stays correct even when the user scrolls
    const currentLaneEl = document.querySelector<HTMLElement>(`.lane-col[data-group-id="${laneKey}"]`)
    const freshLaneTop = currentLaneEl
      ? currentLaneEl.getBoundingClientRect().top
      : initialLaneTop
    // Re-derive startPx relative to the fresh lane top so both coordinates share
    // the same origin (prevents drift when the user scrolls mid-drag).
    const freshStartPx = startClientY - freshLaneTop
    const freshCurrentPx = e.clientY - freshLaneTop
    creating.value = {
      laneKey,
      groupId,
      startPx: freshStartPx,
      currentPx: Math.max(freshStartPx + 5 * MINUTE_PX, freshCurrentPx),
      laneRect: currentLaneEl?.getBoundingClientRect() ?? laneEl.getBoundingClientRect(),
    }
  }

  const onUp = async () => {
    document.removeEventListener('mousemove', onMove)
    if (!hasDragged || !creating.value) {
      creating.value = null
      return
    }
    const startOffset = Math.round(createTopPx.value / MINUTE_PX)
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
  if (!canManage.value) return
  if (plannerStore.saving || plannerStore.loading) return
  const blockId = event.dataTransfer?.getData('application/x-library-block-id')
  if (!blockId) return

  const title = event.dataTransfer?.getData('application/x-library-block-title') ?? ''
  const durationStr = event.dataTransfer?.getData('application/x-library-block-duration') ?? '15'
  const duration = Math.min(sessionDuration.value, parseInt(durationStr) || 15)
  const colorStr = event.dataTransfer?.getData('application/x-library-block-color') ?? ''

  const laneEl = event.currentTarget as HTMLElement
  // getBoundingClientRect().top is viewport-relative and already accounts for the
  // scroll offset of .planner-scroll; adding scrollTop again would double-count it.
  const offsetPx = event.clientY - laneEl.getBoundingClientRect().top
  const startOffset = Math.min(sessionDuration.value - duration, Math.max(0, Math.round(offsetPx / MINUTE_PX / 5) * 5))

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
    duration_minutes: Math.min(sessionDuration.value, libraryBlock.default_duration_minutes ?? 15),
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
  if (!canManage.value) { readingBlock.value = block; return }
  if (dragOccurred || plannerStore.saving) return
  plannerStore.selectBlock(block.id)
  editingBlock.value = block
  showEditDialog.value = true
}

async function createBlock() {
  const added = await plannerStore.addBlock({ session: props.sessionId, title: 'Neuer Baustein', duration_minutes: Math.min(configuration.default_block_duration_minutes, sessionDuration.value) })
  if (added) openEdit(plannerStore.blocks.find((b) => b.id === added.id)!)
}

function onKeyboardMove(id: number, values: TrainingBlockMove) {
  const block = blocks.value.find((b) => b.id === id)
  if (!block) return
  if (values.start_offset_minutes !== undefined) values.start_offset_minutes = Math.max(0, Math.min(sessionDuration.value - block.duration_minutes, values.start_offset_minutes))
  if (values.duration_minutes !== undefined) values.duration_minutes = Math.max(1, Math.min(sessionDuration.value - block.start_offset_minutes, values.duration_minutes))
  plannerStore.stageMove(id, values)
}

function onEditorKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (target.closest('input, textarea, [contenteditable="true"]') || showEditDialog.value || showSessionSettings.value) return
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
    event.preventDefault()
    if (event.shiftKey) plannerStore.redo()
    else plannerStore.undo()
  }
}

function onBlockSaved(_blockId: number) { /* store updated */ }

function onSessionDraft(data: TrainingSessionCreate, choices: GroupMini[]) {
  plannerStore.stageSession(data, choices)
  showSessionSettings.value = false
}

function discardForServerVersion() {
  if (window.confirm('Lokale Änderungen verwerfen und den aktuellen Serverstand laden?')) {
    plannerStore.discardForServerVersion()
    saveFailed.value = false
  }
}

async function stageStatus(status: TrainingStatus) {
  if (!plannerStore.session) return
  if (status === 'published') {
    // Publishing despite planning warnings needs a stored justification.
    await plannerStore.checkDraft()
    if (plannerStore.warnings.length) {
      showJustification.value = true
      return
    }
  }
  plannerStore.stageSession({ status })
}

function focusBlock(id: number) {
  plannerStore.selectBlock(id)
  void nextTick(() => document.querySelector<HTMLElement>(`[data-block-id="${id}"]`)?.focus())
}

// Re-check the local draft shortly after every change (warnings only, nothing is saved).
let checkTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => [plannerStore.session, plannerStore.blocks],
  () => {
    clearTimeout(checkTimer)
    if (!canManage.value || !plannerStore.session) return
    checkTimer = setTimeout(() => { void plannerStore.checkDraft() }, 700)
  },
  { deep: true },
)
onBeforeUnmount(() => clearTimeout(checkTimer))

async function saveAll() {
  const confirmed = !!session.value?.requires_service_confirmation
  if (confirmed && !window.confirm('Der Dienst hat begonnen oder enthält Dokumentation. Plan und Status ausdrücklich ändern? Bestehende Anwesenheiten bleiben erhalten.')) return
  saving.value = true
  saveFailed.value = false
  try { await plannerStore.savePendingMoves(confirmed) }
  catch { saveFailed.value = true }
  finally { saving.value = false }
}

const pendingLabel = computed(() => {
  return 'Ungespeicherter Planentwurf'
})

const laneSummary = computed(() => {
  const groups = visibleLanes.value.filter((lane) => lane.groupId !== null).length
  return groups ? `${groups} ${groups === 1 ? 'Gruppe' : 'Gruppen'}` : ''
})

function formatTimeRange(start: string, end?: string) {
  const short = (t: string) => t.slice(0, 5)
  return end ? `${short(start)}–${short(end)}` : `ab ${short(start)}`
}

function goHandout() {
  router.push(`/training/sessions/${props.sessionId}/handout`)
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE', {
    weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric',
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

function hasUnsavedChanges() {
  return plannerStore.isDirty || plannerStore.saving || showEditDialog.value || showSessionSettings.value
}
function confirmLeave() {
  return !hasUnsavedChanges() || window.confirm('Ungespeicherte Planänderungen gehen verloren. Seite trotzdem verlassen?')
}
function beforeUnload(event: BeforeUnloadEvent) {
  if (!hasUnsavedChanges()) return
  event.preventDefault()
  event.returnValue = ''
}
onBeforeRouteLeave(confirmLeave)
onBeforeRouteUpdate(confirmLeave)
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
watch(() => props.sessionId, async (id) => {
  showEditDialog.value = false
  showSessionSettings.value = false
  editingBlock.value = null
  showPlanAction.value = false
  saveFailed.value = false
  plannerStore.reset()
  try { await plannerStore.loadBlocks(id) }
  catch { return }
  await nextTick()
  if (plannerStore.sessionId === id) setupInteract()
}, { immediate: true })
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnload)
  interact('.block-tile').unset()
  plannerStore.reset()
})

function setupInteract() {
  if (!canManage.value) return
  interact('.block-tile')
    .draggable({
      listeners: {
        start(event) {
          dragOccurred = false
          plannerStore.beginGesture()
          const blockId = parseInt(event.target.dataset.blockId)
          event.target.dataset.currentTop = event.target.style.top || '0'
          event.target.classList.add('dragging')
          plannerStore.selectBlock(blockId)
        },
        move(event) {
          dragOccurred = true
          const blockId = parseInt(event.target.dataset.blockId)
          const prev = parseFloat(event.target.dataset.currentTop ?? '0')
          const block = blocks.value.find((b) => b.id === blockId)
          const rawTop = Math.min(Math.max(0, sessionDuration.value - (block?.duration_minutes ?? 1)) * MINUTE_PX, Math.max(0, prev + event.dy))
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
            const blockId = parseInt(event.target.dataset.blockId)
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
            // Keep the flag true long enough to swallow the synthetic click event
            setTimeout(() => { dragOccurred = false }, 150)
          }
          plannerStore.endGesture()
          delete event.target.dataset.currentTop
          delete event.target.dataset.targetLane
        },
      },
    })
    .resizable({
      edges: { bottom: '.resize-handle' },
      listeners: {
        start(event) {
          dragOccurred = false
          plannerStore.beginGesture()
          // Capture initial height to avoid fighting Vue's reactive :style binding
          event.target.dataset.currentHeight = String(event.target.offsetHeight)
        },
        move(event) {
          dragOccurred = true
          const blockId = parseInt(event.target.dataset.blockId)
          // Accumulate delta manually (event.deltaRect.bottom = change in bottom edge)
          const prev = parseFloat(event.target.dataset.currentHeight ?? String(MINUTE_PX * 15))
          const block = blocks.value.find((b) => b.id === blockId)
          const available = Math.max(1, sessionDuration.value - (block?.start_offset_minutes ?? 0)) * MINUTE_PX
          const rawHeight = Math.min(available, Math.max(MINUTE_PX, prev + event.deltaRect.bottom))
          event.target.dataset.currentHeight = String(rawHeight)
          // Snap to 1-minute increments
          const snapped = Math.max(MINUTE_PX, Math.round(rawHeight / MINUTE_PX) * MINUTE_PX)
          event.target.style.height = `${snapped}px`
          plannerStore.stageMove(blockId, { duration_minutes: Math.round(snapped / MINUTE_PX) })
        },
        end(event) {
          if (dragOccurred) setTimeout(() => { dragOccurred = false }, 150)
          plannerStore.endGesture()
          delete event.target.dataset.currentHeight
        },
      },
    })
}

</script>

<style scoped>
/* ── Outer shell ──────────────────────────────────────────────────────── */
.plan-conflict { padding: var(--jf-space-2); overflow: auto; max-height: 240px; }
.swimlane-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--jf-color-card);
  overflow: hidden;
}

/* Header (WorkspaceHeader): on phones status, "Speichern" and the menu share one row. */
.planner-head--sm :deep(.workspace-head__actions) {
  flex: 1 1 100%;
  flex-wrap: nowrap;
  min-width: 0;
}
.planner-head--sm .save-hint {
  flex: 1 1 auto;
  min-width: 0;
  white-space: nowrap;
}
.save-hint {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  margin-right: var(--jf-space-0-5);
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text-muted);
}
.save-hint--dirty { color: var(--p-amber-800); }
.save-hint--error { color: var(--p-red-700); }
.app-dark .save-hint--dirty { color: var(--p-amber-300); }
.app-dark .save-hint--error { color: var(--p-red-300); }

/* ── Planner container ────────────────────────────────────────────────── */
.planner-container {
  position: relative;
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
  background: var(--jf-color-card);
  border-bottom: 1px solid var(--jf-color-border);
  height: 44px;
}

.time-corner {
  width: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--jf-color-text-muted);
  border-right: 1px solid var(--jf-color-border);
  position: sticky;
  left: 0;
  background: var(--jf-color-card);
  z-index: 11;
}

.lane-header-cell {
  min-width: 200px;
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 var(--jf-space-1-5);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-bold);
  border-right: 1px solid var(--jf-color-border);
  color: var(--jf-color-text);
  background: var(--jf-color-card);
}
.lane-header-cell:last-child { border-right: none; }

/* ── Loading ──────────────────────────────────────────────────────────── */
.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1-5);
  height: 300px;
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
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
  background: var(--jf-color-card);
  border-right: 1px solid var(--jf-color-border);
}

.ruler-label {
  position: absolute;
  right: 6px;
  transform: translateY(-50%);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text-muted);
  white-space: nowrap;
  pointer-events: none;
  z-index: 1;
}

/* The first mark sits at the top edge and would hide under the sticky header */
.ruler-label:first-child { transform: none; }

.ruler-hline {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: color-mix(in srgb, var(--jf-color-border) 50%, transparent);
}
.ruler-hline--hour { background: var(--jf-color-border); }
.ruler-hline--quarter { background: color-mix(in srgb, var(--jf-color-border) 70%, transparent); }

/* ── Lane columns ─────────────────────────────────────────────────────── */
.lanes-wrap {
  flex: 1;
  display: flex;
}

.lane-col {
  flex: 1;
  min-width: 200px;
  position: relative;
  border-right: 1px solid var(--jf-color-border);
  cursor: crosshair;
  background: var(--jf-color-card);
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
.grid-line--quarter { background: color-mix(in srgb, var(--jf-color-border) 45%, transparent); }
.grid-line--hour { background: var(--jf-color-border); }

/* ── Drag-to-create preview ───────────────────────────────────────────── */
.create-preview {
  position: absolute;
  left: 4px;
  right: 4px;
  background: color-mix(in srgb, var(--jf-color-primary) 10%, transparent);
  border: 2px dashed var(--jf-color-primary);
  border-radius: var(--jf-radius-md);
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 4;
}
.create-preview__label {
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  color: var(--jf-color-primary);
  text-align: center;
  padding: 0 var(--jf-space-0-5);
}

/* ── "All Groups" ghost hatching ──────────────────────────────────────── */
.all-groups-ghost {
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
  z-index: 1;
  background-image: repeating-linear-gradient(
    -45deg,
    color-mix(in srgb, var(--jf-color-text-muted) 14%, transparent) 0px,
    color-mix(in srgb, var(--jf-color-text-muted) 14%, transparent) 2px,
    transparent 2px,
    transparent 10px
  );
  border-top: 1px solid var(--jf-color-border);
  border-bottom: 1px solid var(--jf-color-border);
}

/* ── Library panel ────────────────────────────────────────────────────── */
/* Width set by the user (UX-09), never more than half of the planner. */
.library-panel {
  position: relative;
  width: var(--library-width, 320px);
  max-width: 50%;
  flex-shrink: 0;
  border-left: 1px solid var(--jf-color-border);
  background: var(--jf-color-card);
}
.library-panel > :deep(.library-picker) { overflow: hidden; }

.library-resizer {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -8px;
  z-index: 12;
  width: 16px;
  cursor: col-resize;
  touch-action: none;
}
/* Visible line plus a grip in the middle */
.library-resizer::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 7px;
  width: 2px;
  background: transparent;
  transition: background var(--jf-duration);
}
.library-resizer::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 4px;
  width: 8px;
  height: var(--jf-touch-target);
  transform: translateY(-50%);
  border: 1px solid var(--jf-color-border);
  border-radius: 999px;
  background: var(--jf-color-card);
}
.library-resizer:hover::after,
.library-resizer:focus-visible::after { background: var(--jf-color-primary); }
.library-resizer:hover::before,
.library-resizer:focus-visible::before { border-color: var(--jf-color-primary); }
.library-resizer:focus-visible { outline: var(--jf-focus-ring); outline-offset: -2px; border-radius: var(--jf-radius-sm); }
/* Touch: a 44 px wide target around the grip */
@media (pointer: coarse) {
  .library-resizer { left: -22px; width: 44px; }
  .library-resizer::after { left: 21px; }
  .library-resizer::before { left: 18px; }
}

/* Below the desktop layout the library slides over the plan instead of narrowing it. */
@media (max-width: 1023px) {
  .library-panel {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 20;
    width: min(100%, 360px);
    max-width: none;
    box-shadow: var(--jf-shadow-lg);
  }
  .library-resizer { display: none; }
}

/* ── Slide transition ─────────────────────────────────────────────────── */
.slide-panel-enter-active,
.slide-panel-leave-active { transition: width var(--jf-duration) ease; overflow: hidden; }
.slide-panel-enter-from,
.slide-panel-leave-to { width: 0; }
@media (prefers-reduced-motion: reduce) {
  .slide-panel-enter-active,
  .slide-panel-leave-active,
  .library-resizer::after { transition: none; }
}
</style>
