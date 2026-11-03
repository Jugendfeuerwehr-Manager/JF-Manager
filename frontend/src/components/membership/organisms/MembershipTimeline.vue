<template>
  <section class="timeline" aria-labelledby="membership-timeline-heading">
    <header class="timeline__head">
      <h2 id="membership-timeline-heading">Mitgliedschaft</h2>
      <p class="timeline__hint">Zugänge, Stufenwechsel und Abgänge. Daraus entsteht die Jahresmeldung.</p>
    </header>

    <p v-if="store.loading" class="timeline__state">Lade Verlauf …</p>
    <p v-else-if="store.error" class="timeline__state timeline__state--error" role="alert">{{ store.error }}</p>
    <p v-else-if="!store.events.length" class="timeline__state">Noch keine Einträge.</p>

    <ol v-else class="timeline__list">
      <li v-for="event in store.events" :key="event.id" class="timeline__item" :data-kind="direction(event)">
        <span class="timeline__dot" aria-hidden="true"></span>
        <div class="timeline__body">
          <p class="timeline__title">
            <strong>{{ event.kind_label }}</strong>
            <span v-if="event.department_name" class="timeline__meta"> · {{ event.department_name }}</span>
          </p>
          <p class="timeline__meta">
            <time :datetime="event.date">{{ formatDate(event.date) }}</time>
            <template v-if="event.from_status_name || event.to_status_name">
              · {{ event.from_status_name ?? '–' }} → {{ event.to_status_name ?? '–' }}
            </template>
            <template v-if="event.exit_reason_label"> · Grund: {{ event.exit_reason_label }}</template>
          </p>

          <div v-if="needsReason(event)" class="timeline__fix">
            <label :for="`reason-${event.id}`">Grund fehlt für die Jahresmeldung</label>
            <select
              v-if="canEdit"
              :id="`reason-${event.id}`"
              class="timeline__select"
              :disabled="savingId === event.id"
              @change="completeReason(event, ($event.target as HTMLSelectElement).value as ExitReason)"
            >
              <option value="" selected disabled>Grund wählen …</option>
              <option v-for="(label, value) in EXIT_REASON_LABELS" :key="value" :value="value">{{ label }}</option>
            </select>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useMembershipStore } from '@/stores/membership'
import { EXIT_REASON_LABELS, type ExitReason, type MembershipEvent } from '@/types/membership'

interface Props {
  memberId: number
  canEdit?: boolean
}

const props = withDefaults(defineProps<Props>(), { canEdit: false })
const store = useMembershipStore()
const savingId = ref<number | null>(null)

const formatDate = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('de-DE')

function direction(event: MembershipEvent) {
  if (event.kind.startsWith('joined')) return 'join'
  if (event.kind.startsWith('exit')) return 'exit'
  return 'stage'
}

function needsReason(event: MembershipEvent) {
  return event.kind === 'exit_other' && !event.exit_reason
}

async function completeReason(event: MembershipEvent, reason: ExitReason) {
  if (!reason) return
  savingId.value = event.id
  try {
    await store.correctEvent(event.id, { exit_reason: reason })
  } catch {
    // store.error is shown above the list
  } finally {
    savingId.value = null
  }
}

onMounted(() => store.fetchMemberEvents(props.memberId))
watch(
  () => props.memberId,
  (id) => store.fetchMemberEvents(id)
)
</script>

<style scoped>
.timeline__head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: var(--jf-weight-semibold);
}

.timeline__hint,
.timeline__state,
.timeline__meta {
  margin: 0;
  font-size: 0.875rem;
  color: var(--jf-color-text-muted);
}

.timeline__state {
  padding: var(--jf-space-2) 0;
}

.timeline__state--error {
  color: var(--p-red-700);
}

.timeline__list {
  list-style: none;
  margin: var(--jf-space-2) 0 0;
  padding: 0;
  border-left: 2px solid var(--jf-color-border, #d4d4d8);
}

.timeline__item {
  position: relative;
  padding: 0 0 var(--jf-space-2) var(--jf-space-2);
}

.timeline__dot {
  position: absolute;
  left: -7px;
  top: 0.3rem;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--jf-color-text-muted);
}

.timeline__item[data-kind='join'] .timeline__dot {
  background: var(--p-green-600);
}

.timeline__item[data-kind='exit'] .timeline__dot {
  background: var(--p-red-600);
}

.timeline__title {
  margin: 0;
}

.timeline__fix {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  margin-top: var(--jf-space-1);
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  font-size: 0.875rem;
}

.timeline__select {
  min-height: 44px;
  padding: 0 var(--jf-space-1);
  border: 1px solid var(--jf-color-border, #d4d4d8);
  border-radius: var(--jf-radius-md);
  background: var(--p-content-background);
  color: inherit;
  font: inherit;
}
</style>
