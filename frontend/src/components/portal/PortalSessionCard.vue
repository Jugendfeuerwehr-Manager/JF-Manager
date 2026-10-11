<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import PortalStatusChip from './PortalStatusChip.vue'
import type { PortalPerson, PortalSessionItem } from '@/api/portal'
import type { PortalActionError } from '@/stores/portal'
import { deadlineText, describeSession, placesText, positionLines, sessionMeta, type SessionAction } from '@/utils/portalSessions'

const props = defineProps<{ item: PortalSessionItem, person: PortalPerson | null, busy?: boolean, error?: PortalActionError | null }>()
const emit = defineEmits<{ action: [action: SessionAction] }>()

const view = computed(() => describeSession(props.item, props.person))
const places = computed(() => placesText(props.item))
const positions = computed(() => positionLines(props.item))
const deadline = computed(() => (view.value.action && view.value.enabled ? deadlineText(props.item) : null))
const unavailable = computed(() => view.value.chip === 'unavailable')
const blockedId = computed(() => `blocked-${props.item.id}`)
</script>

<template>
  <article class="card" :class="{ dashed: unavailable }" :data-session="item.id">
    <div class="top">
      <div class="titles">
        <span class="meta">{{ sessionMeta(item) }}</span>
        <RouterLink class="title" :to="{ name: 'portal-session', params: { id: item.id } }">{{ item.title }}</RouterLink>
      </div>
      <PortalStatusChip :status="view.chip" />
    </div>

    <p v-if="view.notice" class="hint strong notice" role="status"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> {{ view.notice }}</p>
    <p v-if="view.hint" class="hint">{{ view.hint }}</p>
    <div v-if="places" class="places">
      <div class="row"><span>{{ places.text }}</span><span v-if="deadline" class="muted">{{ deadline }}</span></div>
      <div v-if="places.ratio !== null" class="bar" aria-hidden="true"><div :style="{ width: `${Math.round(places.ratio * 100)}%` }"></div></div>
    </div>
    <p v-else-if="deadline" class="hint">{{ deadline }}</p>
    <ul v-if="positions.length" class="positions" aria-label="Positionen">
      <li v-for="p in positions" :key="p.id" :class="{ full: p.full }"><span>{{ p.label }}</span><span class="muted"><i v-if="p.full" class="pi pi-ban" aria-hidden="true"></i> {{ p.text }}</span></li>
    </ul>

    <template v-if="unavailable">
      <p class="hint strong">Voraussetzung nicht erfüllt:</p>
      <ul class="reasons"><li v-for="r in view.unavailableReasons" :key="r">{{ r }}</li></ul>
    </template>

    <Button
      v-if="view.action"
      type="button"
      class="action"
      :label="view.action.label"
      :severity="view.action.emphasis === 'primary' ? undefined : 'secondary'"
      :outlined="view.action.emphasis === 'secondary'"
      :text="view.action.emphasis === 'text'"
      :loading="busy"
      :disabled="!view.enabled || busy"
      :aria-describedby="view.blocked ? blockedId : undefined"
      @click="emit('action', view.action)"
    />
    <p v-if="view.blocked" :id="blockedId" class="hint">{{ view.blocked }}</p>
    <p v-if="error" class="error" role="alert">
      {{ error.message }}
      <template v-for="r in error.reasons" :key="r"><br />{{ r }}</template>
    </p>
  </article>
</template>

<style scoped>
.card { background: var(--p-content-background); border: 1px solid var(--p-content-border-color); border-radius: 14px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.card.dashed { border-style: dashed; }
.top { display: flex; justify-content: space-between; gap: 8px; }
.titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.meta { font-size: 13px; color: var(--p-text-muted-color); }
.title { font-size: 16px; font-weight: 650; color: var(--p-text-color); text-decoration: none; overflow-wrap: anywhere; }
.title:hover { text-decoration: underline; }
.top :deep(.portal-chip) { align-self: flex-start; }
.hint { margin: 0; font-size: 13px; color: var(--p-text-muted-color); }
.hint.strong { color: var(--p-text-color); }
.reasons { margin: 0; padding-left: 18px; font-size: 13px; }
.places { display: flex; flex-direction: column; gap: 6px; }
.row { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; }
.muted { color: var(--p-text-muted-color); }
.bar { height: 6px; background: var(--p-content-border-color); border-radius: 3px; overflow: hidden; }
.bar div { height: 6px; background: var(--p-primary-color); }
.action { min-height: 44px; border-radius: 10px; }
.positions { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.positions li { display: flex; justify-content: space-between; gap: 8px; }
.error { margin: 0; font-size: 13px; color: var(--p-red-600); }
.app-dark .error { color: var(--p-red-300); }
</style>
