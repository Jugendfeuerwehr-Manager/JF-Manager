<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import PortalAbsenceDialog from './PortalAbsenceDialog.vue'
import PortalCancelSheet from './PortalCancelSheet.vue'
import PortalEmptyCard from './PortalEmptyCard.vue'
import PortalSessionCard from './PortalSessionCard.vue'
import type { PortalAbsenceResult } from '@/api/portal'
import { usePortalSessionActions } from '@/composables/usePortalSessionActions'
import { usePortalStore } from '@/stores/portal'
import { formatDay, monthKey, monthLabel } from '@/utils/portalSessions'

const props = defineProps<{ limit?: number, grouped?: boolean }>()

const portal = usePortalStore()
const { sheetItem, sheetError, run, submitCancel, closeSheet } = usePortalSessionActions()
const absenceOpen = ref(false)
const absenceResult = ref<PortalAbsenceResult | null>(null)

const shown = computed(() => (props.limit ? portal.sessions.slice(0, props.limit) : portal.sessions))
const groups = computed(() => {
  if (!props.grouped) return [{ key: 'all', label: '', items: shown.value }]
  const out: { key: string, label: string, items: typeof portal.sessions }[] = []
  for (const item of shown.value) {
    const key = monthKey(item.date)
    const last = out[out.length - 1]
    if (last && last.key === key) last.items.push(item)
    else out.push({ key, label: monthLabel(key), items: [item] })
  }
  return out
})

watch(() => portal.selectedPersonId, id => { absenceResult.value = null; void portal.loadSessions(id) }, { immediate: true })

function onAbsenceDone(result: PortalAbsenceResult) {
  absenceOpen.value = false
  absenceResult.value = result
}
const resultText = computed(() => {
  const r = absenceResult.value
  if (!r) return ''
  const done = r.cancelled.length === 1 ? '1 Dienst abgemeldet' : `${r.cancelled.length} Dienste abgemeldet`
  return r.skipped.length ? `${done}, ${r.skipped.length} übersprungen.` : `${done}.`
})
</script>

<template>
  <div class="list">
    <div v-if="portal.sessionsLoading && !portal.sessionsLoaded" class="state" role="status">
      <ProgressSpinner style="width: 2rem; height: 2rem" aria-label="Wird geladen" />
    </div>
    <Message v-else-if="portal.sessionsError" severity="error" :closable="false">
      <div class="error-row">
        <span>{{ portal.sessionsError }}</span>
        <Button label="Erneut versuchen" size="small" severity="secondary" @click="portal.loadSessions()" />
      </div>
    </Message>
    <PortalEmptyCard v-else-if="!portal.sessions.length" icon="pi pi-calendar" title="Noch keine geplanten Dienste">
      Sobald Dienste veröffentlicht sind, kannst du hier an- und abmelden.
    </PortalEmptyCard>
    <template v-else>
      <p v-if="resultText" class="result" role="status">
        {{ resultText }}
        <template v-for="s in absenceResult?.skipped" :key="s.id"><br />Übersprungen: {{ s.title }}, {{ formatDay(s.date) }} ({{ s.detail }})</template>
      </p>
      <section v-for="g in groups" :key="g.key" class="group" :aria-label="g.label || 'Termine'">
        <h2 v-if="g.label">{{ g.label }}</h2>
        <PortalSessionCard
          v-for="item in g.items" :key="item.id" :item="item" :person="portal.selectedPerson"
          :busy="portal.pendingSessionIds.includes(item.id)" :error="portal.actionError?.sessionId === item.id ? portal.actionError : null"
          @action="run(item, $event)"
        />
      </section>
      <slot name="more" />
    </template>

    <Button
      v-if="portal.sessionsLoaded && portal.selectedPerson" type="button" class="absence" icon="pi pi-calendar" label="Zeitraum abmelden (z. B. Urlaub)"
      severity="secondary" outlined @click="absenceOpen = true"
    />

    <PortalCancelSheet
      v-if="sheetItem" :item="sheetItem" :person="portal.selectedPerson" :busy="portal.pendingSessionIds.includes(sheetItem.id)"
      :error="sheetError" @close="closeSheet" @submit="submitCancel"
    />
    <PortalAbsenceDialog v-if="absenceOpen" :person="portal.selectedPerson" @close="absenceOpen = false" @done="onAbsenceDone" />
  </div>
</template>

<style scoped>
.list { display: flex; flex-direction: column; gap: 12px; }
.group { display: flex; flex-direction: column; gap: 12px; }
h2 { margin: 8px 0 0; font-size: 14px; font-weight: 650; color: var(--p-text-muted-color); }
.state { display: flex; justify-content: center; padding: 2rem; }
.error-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
.result { margin: 0; padding: 10px 12px; border-radius: 10px; font-size: 14px; background: var(--p-content-hover-background, var(--p-surface-50)); border: 1px solid var(--p-content-border-color); }
.absence { margin-top: 4px; min-height: 48px; border-radius: 12px; }
</style>
