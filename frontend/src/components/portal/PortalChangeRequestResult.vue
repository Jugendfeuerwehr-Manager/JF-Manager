<script setup lang="ts">
import { computed } from 'vue'
import type { ChangeRequest } from '@/types/changeRequests'
import { requestDate } from '@/utils/changeRequestFields'

const props = defineProps<{ request: ChangeRequest }>()

const view = computed(() => {
  switch (props.request.status) {
    case 'applied': return { icon: 'pi pi-check-circle', title: 'Änderung übernommen', tone: 'ok' }
    case 'partial': return { icon: 'pi pi-exclamation-circle', title: 'Änderung teilweise übernommen', tone: 'warn' }
    default: return { icon: 'pi pi-times-circle', title: 'Änderung abgelehnt', tone: 'neutral' }
  }
})
const decision = (d?: string) => (d === 'apply' ? 'übernommen' : d === 'reject' ? 'abgelehnt' : '')
</script>

<template>
  <section class="result" :class="`result--${view.tone}`" role="status" :aria-label="view.title">
    <div class="head"><i :class="view.icon" aria-hidden="true"></i><strong>{{ view.title }}</strong><span class="date">{{ requestDate(request.decided_at ?? request.updated_at) }}</span></div>
    <ul>
      <li v-for="f in request.fields" :key="f.field">{{ f.label }}: {{ f.new || '–' }} <span class="state">({{ decision(f.decision) }})</span></li>
    </ul>
    <p v-if="request.decision_note" class="note">Nachricht der Jugendleitung: {{ request.decision_note }}</p>
  </section>
</template>

<style scoped>
.result { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-radius: 12px; font-size: 14px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
.head { display: flex; align-items: center; gap: 8px; }
.date { margin-left: auto; font-size: 12px; color: var(--p-text-muted-color); }
ul { margin: 0; padding-left: 18px; font-size: 13px; overflow-wrap: anywhere; }
.state { color: var(--p-text-muted-color); }
.note { margin: 0; }
.result--ok .head i { color: var(--p-green-700); }
.result--warn .head i { color: var(--p-orange-700); }
.app-dark .result--ok .head i { color: var(--p-green-300); }
.app-dark .result--warn .head i { color: var(--p-orange-300); }
</style>
