<template>
  <div class="board">
    <p v-if="store.loading && !board" role="status"><i class="pi pi-spin pi-spinner" aria-hidden="true"></i> Zuteilung wird geladen …</p>
    <div v-else-if="!board" role="alert">
      <p>{{ store.error ?? 'Die Zuteilung ist nicht verfügbar.' }}</p>
      <Button label="Erneut laden" severity="secondary" @click="store.load(sessionId)" />
    </div>
    <template v-else>
      <div class="board__head">
        <div class="board__status">
          <StatusBadge v-if="board.staffing?.required" :label="staffingText" :severity="staffingMet ? 'success' : 'warning'" :icon="staffingMet ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'" />
          <StatusBadge v-if="board.published_at" :label="`Veröffentlicht ${formatDateTime(board.published_at)}`" severity="info" icon="pi pi-send" />
          <StatusBadge v-else label="Noch nicht veröffentlicht" severity="neutral" icon="pi pi-clock" />
          <StatusBadge v-if="store.unpublished" label="Entwurf weicht von der Veröffentlichung ab" severity="warning" icon="pi pi-pencil" />
        </div>
        <div v-if="canManage" class="board__actions">
          <Button label="Entwurf speichern" icon="pi pi-save" severity="secondary" :disabled="!store.dirty" :loading="store.saving && !publishing" @click="store.save()" />
          <Button label="Zuteilung veröffentlichen" icon="pi pi-send" :disabled="store.saving || (!store.unpublished && !!board.published_at)" @click="publishOpen = true" />
        </div>
      </div>

      <div v-if="store.conflict" class="board__conflict" role="alert">
        <p><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>{{ ASSIGNMENT_STALE }} Dein Entwurf bleibt erhalten.</p>
        <div class="board__row">
          <Button label="Meinen Entwurf auf neuen Stand übertragen" severity="secondary" @click="store.keepDraftOnServerVersion()" />
          <Button label="Neuen Stand laden und Entwurf verwerfen" severity="secondary" text @click="store.useServerVersion()" />
        </div>
      </div>
      <div v-else-if="store.error" class="board__error" role="alert">
        <p><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ store.error }}</p>
        <ul v-if="store.reasons.length"><li v-for="r in store.reasons" :key="r">{{ r }}</li></ul>
      </div>
      <p class="sr-only" role="status" aria-live="polite">{{ store.notice }}</p>

      <div class="board__columns">
        <section class="board__applicants" aria-labelledby="board-applicants-title" :class="{ 'board__zone--over': overTarget === 'pool' }"
          @dragover.prevent="onDragOver('pool')" @dragleave="overTarget = null" @drop.prevent="onDrop(null)">
          <h3 id="board-applicants-title" class="board__title">Bewerbungen ({{ store.unassigned.length }})</h3>
          <div class="board__filters">
            <label for="board-filter">Nur passend für</label>
            <select id="board-filter" v-model="store.onlyFor" class="board__input">
              <option value="all">alle Positionen</option>
              <option v-for="slot in board.slots" :key="slot.id" :value="slot.id">{{ slot.label }}</option>
            </select>
            <label for="board-sort">Sortieren</label>
            <select id="board-sort" v-model="store.sort" class="board__input">
              <option value="applied">nach Bewerbungszeit</option>
              <option value="name">nach Name</option>
              <option value="fairness">nach Zuteilungen (90 Tage)</option>
            </select>
          </div>
          <p v-if="!store.unassigned.length" class="board__muted">Keine offenen Bewerbungen in dieser Ansicht.</p>
          <ul class="board__list">
            <li v-for="person in store.unassigned" :key="person.member_id">
              <article class="card" :class="{ 'card--dragging': dragging === person.member_id }" :draggable="canManage" :aria-label="`${person.name} ${person.lastname}`"
                @dragstart="onDragStart(person, $event)" @dragend="onDragEnd">
                <div class="card__top">
                  <i v-if="canManage" class="pi pi-bars card__grip" aria-hidden="true"></i>
                  <strong>{{ person.name }} {{ person.lastname }}</strong>
                  <StatusBadge v-if="person.state === 'not_selected'" label="nicht berücksichtigt" severity="neutral" icon="pi pi-minus-circle" />
                </div>
                <p class="card__fit">{{ fitText(person) }}</p>
                <p v-if="person.preferred_slot" class="card__muted"><i class="pi pi-star" aria-hidden="true"></i> Wunsch: {{ slotLabel(person.preferred_slot) }}</p>
                <ul v-if="person.qualifications.length" class="chips" aria-label="Qualifikationen">
                  <li v-for="q in person.qualifications" :key="q">{{ q }}</li>
                </ul>
                <p class="card__muted">{{ person.recent_assignments ? `${person.recent_assignments}× zugeteilt in 90 Tagen` : 'Keine Zuteilung in 90 Tagen' }}</p>
                <p v-if="person.conflict" class="card__warn"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> Voraussetzung nicht mehr erfüllt</p>
                <div v-if="canManage" class="card__assign">
                  <label :for="`assign-${person.member_id}`">Zuteilen zu …</label>
                  <select :id="`assign-${person.member_id}`" class="board__input" value="" @change="onSelect(person, $event, '')">
                    <option value="" disabled>Position wählen</option>
                    <option v-for="opt in targetOptions(person)" :key="String(opt.value)" :value="String(opt.value)" :disabled="!!opt.blocked">
                      {{ opt.label }}{{ opt.blocked ? ` – ${opt.blocked}` : '' }}
                    </option>
                  </select>
                </div>
              </article>
            </li>
          </ul>
        </section>

        <section class="board__slots" aria-label="Positionen">
          <div v-for="zone in zones" :key="String(zone.target)" class="zone"
            :class="{ 'zone--over': overTarget === zone.target, 'zone--blocked': dragBlock(zone.target), 'zone--short': zone.short }"
            :aria-disabled="dragBlock(zone.target) ? 'true' : undefined"
            @dragover.prevent="onDragOver(zone.target)" @dragleave="overTarget = null" @drop.prevent="onDrop(zone.target)">
            <div class="zone__head">
              <h3 class="board__title">{{ zone.label }}</h3>
              <span class="zone__count">{{ zone.count }} / {{ zone.max }}<template v-if="zone.min"> · mind. {{ zone.min }}</template></span>
            </div>
            <p v-if="zone.short" class="card__warn"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> Es fehlen {{ zone.min - zone.count }}</p>
            <p v-if="dragBlock(zone.target)" class="zone__reason"><i class="pi pi-ban" aria-hidden="true"></i> {{ dragBlock(zone.target) }}</p>
            <ul class="board__list">
              <li v-for="person in store.inTarget(zone.target)" :key="person.member_id">
                <article class="card card--assigned" :draggable="canManage" :aria-label="`${person.name} ${person.lastname}, ${zone.label}`"
                  @dragstart="onDragStart(person, $event)" @dragend="onDragEnd">
                  <div class="card__top">
                    <i v-if="canManage" class="pi pi-bars card__grip" aria-hidden="true"></i>
                    <strong>{{ person.name }} {{ person.lastname }}</strong>
                    <i v-if="person.preferred_slot === zone.target" class="pi pi-star card__wish" aria-label="Wunschposition" role="img"></i>
                  </div>
                  <div v-if="canManage" class="card__assign">
                    <label :for="`move-${person.member_id}`" class="sr-only">{{ person.name }} umsetzen</label>
                    <select :id="`move-${person.member_id}`" class="board__input" :value="String(zone.target)" @change="onSelect(person, $event, String(zone.target))">
                      <option v-for="opt in targetOptions(person)" :key="String(opt.value)" :value="String(opt.value)" :disabled="!!opt.blocked && opt.value !== zone.target">
                        {{ opt.label }}{{ opt.blocked && opt.value !== zone.target ? ` – ${opt.blocked}` : '' }}
                      </option>
                    </select>
                    <Button icon="pi pi-times" severity="secondary" text :aria-label="`${person.name} ${person.lastname} zurück zu den Bewerbungen`" @click="store.assign(person.member_id, null)" />
                  </div>
                </article>
              </li>
            </ul>
            <p v-if="!store.inTarget(zone.target).length" class="board__muted">Hierher ziehen oder „Zuteilen zu …“ wählen.</p>
          </div>
        </section>
      </div>
    </template>

    <Dialog v-model:visible="publishOpen" modal header="Zuteilung veröffentlichen" :style="{ width: '30rem', maxWidth: 'calc(100vw - 24px)' }">
      <div v-if="board" class="board__publish">
        <p>{{ assignedCount }} Person{{ assignedCount === 1 ? '' : 'en' }} zugeteilt, {{ openCount }} weitere Bewerbung{{ openCount === 1 ? '' : 'en' }}.</p>
        <label class="board__check"><input v-model="keepOpen" type="checkbox"> Bewerbungen offen lassen (sonst „nicht berücksichtigt“)</label>
        <p class="board__muted">Alle Betroffenen erhalten eine Mitteilung. Spätere Änderungen werden einzeln mitgeteilt.</p>
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" text @click="publishOpen = false" />
        <Button label="Veröffentlichen" icon="pi pi-send" :loading="publishing" @click="confirmPublish" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { ASSIGNMENT_STALE, blockReason, useAssignmentStore } from '@/stores/assignment'
import type { BoardApplicant, DraftTarget } from '@/api/participation'

const props = defineProps<{ sessionId: number, canManage?: boolean }>()
const store = useAssignmentStore()
const board = computed(() => store.board)

const dragging = ref<number | null>(null)
const overTarget = ref<DraftTarget | 'pool' | null>(null)
const publishOpen = ref(false)
const publishing = ref(false)
const keepOpen = ref(false)

const slotLabel = (id: number | null) => board.value?.slots.find(s => s.id === id)?.label ?? ''
const fitText = (person: BoardApplicant) => {
  if (!person.general_ok) return `Voraussetzungen nicht erfüllt: ${person.general_reasons.join('; ')}`
  const labels = person.fits.map(slotLabel).filter(Boolean)
  return labels.length ? `passt für: ${labels.join(', ')}` : 'passt zu keiner Position'
}

const zones = computed(() => {
  if (!board.value) return []
  const list = board.value.slots.map(slot => {
    const count = Object.values(store.draft).filter(v => v === slot.id).length
    return { target: slot.id as DraftTarget, label: slot.label, max: slot.max, min: slot.min, count, short: count < slot.min }
  })
  if ((board.value.extra_places ?? 0) > 0 || Object.values(store.draft).includes('extra')) {
    const count = Object.values(store.draft).filter(v => v === 'extra').length
    list.push({ target: 'extra', label: board.value.slots.length ? 'Ohne Position' : 'Teilnehmende', max: board.value.extra_places ?? 0, min: 0, count, short: false })
  }
  return list
})

/** Draft staffing computed locally so the badge follows every move. */
const staffingRows = computed(() => zones.value.filter(z => z.target !== 'extra' && z.min > 0))
const staffingMet = computed(() => staffingRows.value.every(z => !z.short))
const staffingText = computed(() => {
  const missing = staffingRows.value.filter(z => z.short)
  const text = `Mindestbesetzung: ${staffingRows.value.length - missing.length} von ${staffingRows.value.length} erfüllt`
  return missing.length ? `${text} – es fehlt ${missing.map(z => `${z.min - z.count}× ${z.label}`).join(', ')}` : text
})

const assignedCount = computed(() => Object.keys(store.draft).length)
const openCount = computed(() => (board.value?.applicants.length ?? 0) - assignedCount.value)

function targetOptions(person: BoardApplicant) {
  if (!board.value) return []
  return zones.value.map(zone => ({
    value: zone.target,
    label: zone.target === 'extra' ? zone.label : `${zone.label} (${zone.count}/${zone.max})`,
    blocked: blockReason(board.value!, store.draft, person, zone.target),
  }))
}

function onSelect(person: BoardApplicant, event: Event, previous: string) {
  const select = event.target as HTMLSelectElement
  const raw = select.value
  if (!raw) return
  const blocked = store.assign(person.member_id, raw === 'extra' ? 'extra' : Number(raw))
  if (blocked) select.value = previous
}

function onDragStart(person: BoardApplicant, event: DragEvent) {
  if (!props.canManage) return
  dragging.value = person.member_id
  event.dataTransfer?.setData('text/plain', String(person.member_id))
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}
function onDragEnd() { dragging.value = null; overTarget.value = null }
function onDragOver(target: DraftTarget | 'pool') { overTarget.value = target }

/** Reason shown on a zone while a card is dragged over the board (grey and explained, concept 4.7). */
function dragBlock(target: DraftTarget): string | null {
  if (dragging.value === null || !board.value) return null
  const person = board.value.applicants.find(a => a.member_id === dragging.value)
  if (!person || store.draft[person.member_id] === target) return null
  return blockReason(board.value, store.draft, person, target)
}

function onDrop(target: DraftTarget | null) {
  const id = dragging.value
  onDragEnd()
  if (id === null) return
  store.assign(id, target)
}

async function confirmPublish() {
  publishing.value = true
  const ok = await store.publish(keepOpen.value)
  publishing.value = false
  if (ok) publishOpen.value = false
}

const formatDateTime = (iso: string) => new Date(iso).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

onMounted(() => { void store.load(props.sessionId) })
watch(() => props.sessionId, id => { void store.load(id) })
</script>

<style scoped>
.board { display: grid; gap: var(--jf-space-2); }
.board p { margin: 0; }
.board__head { display: flex; flex-wrap: wrap; gap: var(--jf-space-1-5); align-items: center; justify-content: space-between; }
.board__status, .board__actions, .board__row { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); align-items: center; }
.board__actions :deep(.p-button) { min-height: var(--jf-touch-target); }
.board__conflict, .board__error { padding: var(--jf-space-1-5) var(--jf-space-2); border: 1px solid var(--p-amber-600); border-radius: var(--jf-radius-md); background: var(--jf-color-card); display: grid; gap: var(--jf-space-1); }
.board__error { border-color: var(--p-red-600); }
.board__error ul { margin: 0; padding-left: var(--jf-space-2); }
.board__columns { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); gap: var(--jf-space-2); align-items: start; }
.board__applicants, .zone { display: grid; gap: var(--jf-space-1); padding: var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-ground); min-width: 0; }
.board__slots { display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: var(--jf-space-1-5); }
.board__title { margin: 0; font-size: var(--jf-text-base); font-weight: var(--jf-weight-bold); }
.board__filters { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--jf-space-1); align-items: center; font-size: var(--jf-text-sm); }
.board__input { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; width: 100%; box-sizing: border-box; min-width: 0; }
.board__list { margin: 0; padding: 0; list-style: none; display: grid; gap: var(--jf-space-1); }
.board__muted, .card__muted { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.card { display: grid; gap: 4px; padding: var(--jf-space-1) var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); background: var(--jf-color-card); }
.card[draggable='true'] { cursor: grab; }
.card--dragging { opacity: 0.5; }
.card__top { display: flex; align-items: center; gap: var(--jf-space-1); flex-wrap: wrap; }
.card__grip { color: var(--jf-color-text-muted); }
.card__wish { color: var(--p-amber-600); }
.card__fit { font-size: var(--jf-text-sm); }
.card__warn { color: var(--p-amber-700); font-size: var(--jf-text-sm); }
.card__assign { display: flex; gap: var(--jf-space-1); align-items: center; flex-wrap: wrap; font-size: var(--jf-text-sm); }
.card__assign select { flex: 1 1 10rem; }
.card__assign :deep(.p-button) { min-width: var(--jf-touch-target); min-height: var(--jf-touch-target); }
.chips { margin: 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 4px; }
.chips li { padding: 2px 8px; border-radius: 999px; border: 1px solid var(--jf-color-border); font-size: var(--jf-text-xs, 12px); }
.zone__head { display: flex; justify-content: space-between; gap: var(--jf-space-1); align-items: baseline; }
.zone__count { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); white-space: nowrap; }
.zone--short { border-color: var(--p-amber-600); }
.zone--over, .board__zone--over { outline: 2px dashed var(--jf-color-primary); outline-offset: 2px; }
.zone--blocked { opacity: 0.55; border-style: dashed; }
.zone__reason { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.board__publish { display: grid; gap: var(--jf-space-1-5); }
.board__check { display: flex; gap: var(--jf-space-1); align-items: center; min-height: var(--jf-touch-target); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.app-dark .card__warn { color: var(--p-amber-300); }
@media (max-width: 760px) { .board__columns { grid-template-columns: minmax(0, 1fr); } }
</style>
