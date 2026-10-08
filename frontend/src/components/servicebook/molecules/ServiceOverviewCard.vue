<template>
  <article class="overview-card" :class="{ 'overview-card--today': today }">
    <p class="overview-card__when">{{ whenLine }}</p>
    <h3 class="overview-card__title">{{ card.topic || 'Dienst ohne Thema' }}</h3>
    <p v-if="card.groups.length" class="overview-card__groups">{{ card.groups.join(', ') }}</p>
    <dl class="overview-card__counts" :aria-label="`Zähler: ${card.counts.expected} erwartet, ${card.counts.cancelled} abgemeldet, ${card.counts.recorded} erfasst`">
      <div><dt>erwartet</dt><dd>{{ card.counts.expected }}</dd></div>
      <div><dt>abgemeldet</dt><dd>{{ card.counts.cancelled }}</dd></div>
      <div><dt>erfasst</dt><dd>{{ card.counts.recorded }}</dd></div>
    </dl>
    <p v-if="openCount > 0 && !today" class="overview-card__open"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ openCount }} offen</p>
    <div class="overview-card__actions">
      <router-link
        :to="{ name: 'service-attendance', params: { id: card.id } }"
        class="card-action"
        :class="{ 'card-action--primary': today }"
      >
        <i class="pi pi-check-square" aria-hidden="true"></i>{{ today || openCount > 0 ? 'Anwesenheit erfassen' : 'Anwesenheit' }}
      </router-link>
      <router-link
        v-if="today || card.session_id"
        :to="{ name: 'service-detail', params: { id: card.id }, query: { tab: 'registrations' } }"
        class="card-action"
      >
        <i class="pi pi-users" aria-hidden="true"></i>Meldungen ansehen
      </router-link>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ServiceOverviewCard } from '@/types/servicebook'

const props = defineProps<{ card: ServiceOverviewCard; today?: boolean }>()

const openCount = computed(() => Math.max(props.card.counts.total - props.card.counts.recorded, 0))
const whenLine = computed(() => {
  const start = new Date(props.card.start)
  const end = new Date(props.card.end)
  const day = start.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' })
  const time = (d: Date) => d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  return props.today ? `${day} · ${time(start)}–${time(end)}` : `${day} · ${time(start)}`
})
</script>

<style scoped>
.overview-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  padding: var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-sm);
  min-width: 0;
}
.overview-card--today { border-color: var(--jf-color-primary); }
.overview-card__when {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--jf-color-primary);
}
.overview-card__title { margin: 0; font-size: var(--jf-text-lg); overflow-wrap: anywhere; }
.overview-card__groups { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.overview-card__counts {
  display: flex;
  gap: var(--jf-space-3);
  margin: var(--jf-space-1) 0 0;
}
.overview-card__counts div { display: flex; flex-direction: column-reverse; }
.overview-card__counts dt { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.overview-card__counts dd { margin: 0; font-size: var(--jf-text-xl); font-weight: var(--jf-weight-bold); }
.overview-card__open {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--p-amber-900);
}
.app-dark .overview-card__open { color: var(--p-amber-300); }
.overview-card__actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); margin-top: var(--jf-space-1); }
.card-action {
  flex: 1 1 140px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1);
  min-height: 3rem;
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--p-surface-300);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}
.card-action--primary {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}
</style>
