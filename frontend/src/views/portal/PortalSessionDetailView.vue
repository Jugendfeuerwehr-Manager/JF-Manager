<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import PortalCancelSheet from '@/components/portal/PortalCancelSheet.vue'
import PortalPositionSheet from '@/components/portal/PortalPositionSheet.vue'
import PortalEmptyCard from '@/components/portal/PortalEmptyCard.vue'
import { usePortalSessionActions } from '@/composables/usePortalSessionActions'
import { usePortalStore } from '@/stores/portal'
import { describeSession, formatDay, formatDeadline, formatTimeRange, placesText, positionLines, statusBanner } from '@/utils/portalSessions'

const props = defineProps<{ id: number }>()

const portal = usePortalStore()
const { sheetItem, sheetError, run, submitCancel, closeSheet, positionItem, positionError, submitPosition, closePosition } = usePortalSessionActions()

const item = computed(() => portal.sessions.find(s => s.id === props.id) ?? null)
const person = computed(() => portal.selectedPerson)
const view = computed(() => (item.value ? describeSession(item.value, person.value) : null))
const banner = computed(() => (item.value ? statusBanner(item.value, person.value) : null))
const places = computed(() => (item.value ? placesText(item.value) : null))
const positions = computed(() => (item.value ? positionLines(item.value) : []))
const busy = computed(() => portal.pendingSessionIds.includes(props.id))
const error = computed(() => (portal.actionError?.sessionId === props.id ? portal.actionError : null))

function ensureLoaded() {
  const id = portal.selectedPersonId
  if (id === null) return
  if (portal.sessionsPersonId !== id || !portal.sessionsLoaded) void portal.loadSessions(id)
}
onMounted(() => {
  if (!portal.me && !portal.loading) void portal.fetchMe()
  ensureLoaded()
})
watch(() => portal.selectedPersonId, ensureLoaded)
</script>

<template>
  <div class="page">
    <div class="bar">
      <RouterLink :to="{ name: 'portal-sessions' }" class="back" aria-label="Zurück zu den Terminen"><i class="pi pi-chevron-left" aria-hidden="true"></i></RouterLink>
      <span class="bar-title">Termin</span>
    </div>

    <div v-if="portal.sessionsLoading && !item" class="state" role="status">
      <ProgressSpinner style="width: 2rem; height: 2rem" aria-label="Wird geladen" />
    </div>
    <Message v-else-if="portal.sessionsError && !item" severity="error" :closable="false">
      <div class="error-row">
        <span>{{ portal.sessionsError }}</span>
        <Button label="Erneut versuchen" size="small" severity="secondary" @click="portal.loadSessions()" />
      </div>
    </Message>
    <PortalEmptyCard v-else-if="!item" icon="pi pi-calendar" title="Termin nicht gefunden">
      Dieser Termin ist für die ausgewählte Person nicht verfügbar.
    </PortalEmptyCard>

    <section v-else-if="view && banner" class="card" :aria-label="item.title">
      <div class="head">
        <span class="meta">{{ formatDay(item.date, true) }}<template v-if="item.start_time"> · {{ formatTimeRange(item.start_time, item.end_time) }}</template></span>
        <h1>{{ item.title }}</h1>
        <span v-if="item.place" class="place">{{ item.place }}</span>
      </div>

      <div class="banner" :class="`tone-${banner.tone}`" role="status"><i :class="banner.icon" aria-hidden="true"></i>{{ banner.text }}</div>

      <template v-if="view.unavailableReasons">
        <ul class="reasons"><li v-for="r in view.unavailableReasons" :key="r">{{ r }}</li></ul>
      </template>

      <div v-if="places" class="places">
        <div class="row"><span>{{ places.text }}</span><span v-if="item.mode === 'opt_in'" class="muted">Warteliste aktiv</span></div>
        <div v-if="places.ratio !== null" class="meter" aria-hidden="true"><div :style="{ width: `${Math.round(places.ratio * 100)}%` }"></div></div>
      </div>

      <section v-if="positions.length" class="positions" aria-labelledby="detail-positions">
        <h2 id="detail-positions">Positionen</h2>
        <ul>
          <li v-for="p in positions" :key="p.id"><span>{{ p.label }}</span><span class="muted"><i v-if="p.full" class="pi pi-ban" aria-hidden="true"></i> {{ p.text }}</span></li>
        </ul>
      </section>

      <dl class="deadlines">
        <div v-if="item.deadlines.registration_closes_at && item.mode !== 'opt_out'"><dt>Anmeldeschluss</dt><dd>{{ formatDeadline(item.deadlines.registration_closes_at) }}</dd></div>
        <div v-if="item.deadlines.cancellation_closes_at"><dt>Abmeldeschluss</dt><dd>{{ formatDeadline(item.deadlines.cancellation_closes_at) }}</dd></div>
      </dl>

      <div v-if="view.hint" class="muted">{{ view.hint }}</div>

      <Button
        v-if="view.action" type="button" class="action" :label="view.action.label"
        :severity="view.action.emphasis === 'primary' ? undefined : 'secondary'" :outlined="view.action.emphasis === 'secondary'" :text="view.action.emphasis === 'text'"
        :loading="busy" :disabled="!view.enabled || busy" :aria-describedby="view.blocked ? 'detail-blocked' : undefined" @click="run(item, view.action)"
      />
      <p v-if="view.blocked" id="detail-blocked" class="muted">{{ view.blocked }}</p>
      <p v-if="error" class="error" role="alert">{{ error.message }}<template v-for="r in error.reasons" :key="r"><br />{{ r }}</template></p>

      <div v-if="item.public_note" class="note">
        <span class="muted">Hinweis für Teilnehmende</span>
        <p>{{ item.public_note }}</p>
      </div>
    </section>

    <PortalPositionSheet
      v-if="positionItem" :item="positionItem" :person="person" :busy="portal.pendingSessionIds.includes(positionItem.id)"
      :error="positionError" @close="closePosition" @submit="submitPosition"
    />
    <PortalCancelSheet
      v-if="sheetItem" :item="sheetItem" :person="person" :busy="portal.pendingSessionIds.includes(sheetItem.id)"
      :error="sheetError" @close="closeSheet" @submit="submitCancel"
    />
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.bar { display: flex; align-items: center; gap: 4px; margin: -4px 0 0 -8px; }
.back { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: var(--p-text-color); border-radius: 10px; }
.back:focus-visible { outline: 2px solid var(--p-primary-color); }
.bar-title { font-size: 16px; font-weight: 650; }
.state { display: flex; justify-content: center; padding: 2rem; }
.error-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
.card { background: var(--p-content-background); border: 1px solid var(--p-content-border-color); border-radius: 14px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.head { display: flex; flex-direction: column; gap: 4px; }
.meta { font-size: 13px; color: var(--p-text-muted-color); }
h1 { margin: 0; font-size: 22px; font-weight: 700; overflow-wrap: anywhere; }
.place { font-size: 14px; }
.banner { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 10px; font-size: 14px; font-weight: 600; background: var(--b-bg); color: var(--b-fg); }
.tone-success { --b-fg: var(--p-green-800); --b-bg: var(--p-green-100); }
.tone-warning { --b-fg: var(--p-orange-800); --b-bg: var(--p-orange-100); }
.tone-info { --b-fg: var(--p-sky-800); --b-bg: var(--p-sky-100); }
.tone-neutral { --b-fg: var(--p-surface-700); --b-bg: var(--p-surface-100); }
.app-dark .tone-success { --b-fg: var(--p-green-300); --b-bg: color-mix(in srgb, var(--p-green-400), transparent 84%); }
.app-dark .tone-warning { --b-fg: var(--p-orange-300); --b-bg: color-mix(in srgb, var(--p-orange-400), transparent 84%); }
.app-dark .tone-info { --b-fg: var(--p-sky-300); --b-bg: color-mix(in srgb, var(--p-sky-400), transparent 84%); }
.app-dark .tone-neutral { --b-fg: var(--p-surface-200); --b-bg: var(--p-surface-800); }
.reasons { margin: 0; padding-left: 18px; font-size: 14px; }
.places { display: flex; flex-direction: column; gap: 6px; }
.row { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; }
.muted { color: var(--p-text-muted-color); font-size: 13px; }
p.muted { margin: 0; }
.meter { height: 6px; background: var(--p-content-border-color); border-radius: 3px; overflow: hidden; }
.meter div { height: 6px; background: var(--p-primary-color); }
.deadlines { margin: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; font-size: 13px; }
.deadlines div { display: flex; flex-direction: column; gap: 2px; }
dt { color: var(--p-text-muted-color); }
dd { margin: 0; font-weight: 600; }
.action { min-height: 48px; border-radius: 12px; }
.positions h2 { margin: 0 0 6px; font-size: 14px; font-weight: 650; }
.positions ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; font-size: 14px; }
.positions li { display: flex; justify-content: space-between; gap: 8px; }
.error { margin: 0; font-size: 13px; color: var(--p-red-600); }
.app-dark .error { color: var(--p-red-300); }
.note { border-top: 1px solid var(--p-content-border-color); padding-top: 12px; display: flex; flex-direction: column; gap: 4px; }
.note p { margin: 0; font-size: 14px; line-height: 1.45; white-space: pre-line; }
</style>
