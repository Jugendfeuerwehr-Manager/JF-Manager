<template>
  <article class="service-row" :aria-labelledby="`service-${service.id}-title`">
    <span class="date-tile" aria-hidden="true">
      <span class="date-tile__weekday">{{ weekday }}</span>
      <span class="date-tile__day">{{ day }}</span>
      <span class="date-tile__month">{{ month }}</span>
    </span>

    <div class="service-row__text">
      <h3 :id="`service-${service.id}-title`" class="service-row__title">
        <!-- The whole row opens "Dienst bearbeiten", as users know it; the exercise stays one click away. -->
        <router-link :to="{ name: 'service-edit', params: { id: service.id } }" class="service-row__link">
          <span class="visually-hidden">{{ fullDate }}: </span>{{ service.topic || 'Dienst ohne Thema' }}
        </router-link>
      </h3>
      <p class="service-row__meta">{{ [timeRange, service.place].filter(Boolean).join(' · ') }}</p>
      <div class="service-row__badges">
        <TrainingStatusBadge v-if="service.training_status" :status="service.training_status" />
        <StatusBadge v-if="attendanceTotal" severity="success" icon="pi pi-users" :label="attendanceLabel" />
        <StatusBadge v-else-if="isStarted" severity="warning" icon="pi pi-user-plus" label="Anwesenheit offen" />
        <StatusBadge v-if="service.has_events" severity="info" icon="pi pi-flag" label="Besonderheiten" />
        <span v-if="operationsManagerNames" class="service-row__managers"><i class="pi pi-user" aria-hidden="true"></i>{{ operationsManagerNames }}</span>
      </div>
    </div>

    <div v-if="showActions" class="service-row__actions">
      <router-link
        v-if="isStarted"
        :to="{ name: 'service-attendance', params: { id: service.id } }"
        class="row-action row-action--primary"
        :aria-label="`Anwesenheit für ${service.topic || 'Dienst'} am ${fullDate} erfassen`"
      ><i class="pi pi-check-square" aria-hidden="true"></i><span>Anwesenheit</span></router-link>
      <Button
        v-if="service.training_session"
        icon="pi pi-calendar"
        text
        severity="secondary"
        :aria-label="`Übungsplan zu ${service.topic || 'Dienst'} öffnen`"
        v-tooltip.top="'Zur Übung'"
        @click="$emit('open-training', service.training_session)"
      />
      <Button
        icon="pi pi-pencil"
        text
        severity="secondary"
        :aria-label="`${service.topic || 'Dienst'} am ${fullDate} bearbeiten`"
        v-tooltip.top="'Bearbeiten'"
        @click="$emit('edit', service.id)"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import TrainingStatusBadge from '@/components/training/atoms/TrainingStatusBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { Service } from '@/types/servicebook'

interface Props {
  service: Service
  showActions?: boolean
}

interface Emits {
  (e: 'view', id: number): void
  (e: 'edit', id: number): void
  (e: 'open-training', trainingId: number): void
}

const props = withDefaults(defineProps<Props>(), {
  showActions: true
})

defineEmits<Emits>()

const start = computed(() => new Date(props.service.start))
const end = computed(() => new Date(props.service.end))
const weekday = computed(() => start.value.toLocaleDateString('de-DE', { weekday: 'short' }).replace('.', ''))
const day = computed(() => start.value.toLocaleDateString('de-DE', { day: '2-digit' }))
const month = computed(() => start.value.toLocaleDateString('de-DE', { month: 'short' }).replace('.', ''))
const fullDate = computed(() => start.value.toLocaleDateString('de-DE', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' }))
const time = (d: Date) => d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
const timeRange = computed(() => `${time(start.value)}–${time(end.value)}`)

/** Attendance can be taken from the start day on; future services only offer editing. */
const isStarted = computed(() => {
  const endOfToday = new Date()
  endOfToday.setHours(23, 59, 59, 999)
  return start.value <= endOfToday
})

const attendanceTotal = computed(() => {
  const summary = props.service.attendance_summary
  return summary ? summary.present + summary.excused + summary.absent : 0
})

const attendanceLabel = computed(() => {
  const s = props.service.attendance_summary
  return `${s.present} anwesend · ${s.excused} entschuldigt · ${s.absent} ${s.absent === 1 ? 'fehlt' : 'fehlen'}`
})

const operationsManagerNames = computed(() => {
  return props.service.operations_manager?.map((m) => m.full_name).join(', ') || ''
})
</script>

<style scoped>
.service-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1-5) var(--jf-space-2);
}

.date-tile {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 60px;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  line-height: 1.1;
}

.date-tile__weekday,
.date-tile__month {
  font-size: 0.6875rem;
  font-weight: var(--jf-weight-bold);
  text-transform: uppercase;
}

.date-tile__weekday {
  color: var(--jf-color-primary);
}

.date-tile__month {
  color: var(--jf-color-text-muted);
}

.date-tile__day {
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-bold);
}

.service-row__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.service-row__title {
  margin: 0;
  font-size: var(--jf-text-md);
  font-weight: var(--jf-weight-semibold);
  overflow-wrap: anywhere;
}

.service-row__link {
  color: inherit;
  text-decoration: none;
}

/* Stretch the title link over the row; actions stay clickable above it. */
.service-row__link::after {
  content: '';
  position: absolute;
  inset: 0;
}

.service-row:hover {
  background: var(--jf-color-ground);
}

.service-row:has(.service-row__link:focus-visible) {
  outline: var(--jf-focus-ring);
  outline-offset: -2px;
}

.service-row__link:focus-visible {
  outline: none;
}

.service-row__meta {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.service-row__badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-0-5) var(--jf-space-1);
  margin-top: 2px;
}

.service-row__managers {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.service-row__actions {
  position: relative;
  z-index: 1;
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
}

.row-action {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-2);
  border-radius: var(--jf-radius-md);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.row-action--primary {
  border: 1px solid var(--jf-color-primary);
  color: var(--jf-color-primary);
}

.row-action--primary:hover {
  background: var(--jf-color-selected);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@media (max-width: 767px) {
  .service-row {
    flex-wrap: wrap;
    padding: var(--jf-space-1-5);
  }

  .service-row__text {
    flex-basis: calc(100% - 64px);
  }

  .service-row__actions {
    flex: 1 1 100%;
    justify-content: flex-end;
  }

  .row-action--primary {
    flex: 1;
    justify-content: center;
  }
}
</style>
