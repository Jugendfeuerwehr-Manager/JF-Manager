<template>
  <div class="mobile-list">
    <StateView v-if="store.overviewLoading && !hasAny" kind="loading" title="Dienste werden geladen …" />
    <StateView
      v-else-if="store.overviewError"
      :kind="stateForError(store.overviewError)"
      title="Dienste konnten nicht geladen werden"
      @retry="load"
    />
    <template v-else>
      <section v-if="store.overview.today.length" aria-labelledby="ml-today">
        <h2 id="ml-today" class="bucket-title">Heute</h2>
        <div class="bucket">
          <ServiceOverviewCard v-for="card in store.overview.today" :key="card.id" :card="card" today />
        </div>
      </section>
      <section v-if="store.overview.open.length" aria-labelledby="ml-open">
        <h2 id="ml-open" class="bucket-title">Anwesenheit offen</h2>
        <div class="bucket">
          <ServiceOverviewCard v-for="card in store.overview.open" :key="card.id" :card="card" />
        </div>
      </section>
      <section v-if="store.overview.upcoming.length" aria-labelledby="ml-upcoming">
        <h2 id="ml-upcoming" class="bucket-title">Demnächst</h2>
        <div class="bucket">
          <ServiceOverviewCard v-for="card in store.overview.upcoming" :key="card.id" :card="card" />
        </div>
      </section>
      <StateView v-if="!hasAny" kind="empty" title="Keine Dienste" message="Heute, demnächst und offen gibt es keine Dienste." />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import ServiceOverviewCard from '../molecules/ServiceOverviewCard.vue'
import { useServiceRegistrationsStore } from '@/stores/serviceRegistrations'

const props = defineProps<{ department?: number | null }>()
const store = useServiceRegistrationsStore()

const hasAny = computed(() => store.overview.today.length + store.overview.upcoming.length + store.overview.open.length > 0)
const load = () => store.fetchOverview(props.department)

onMounted(load)
watch(() => props.department, load)
</script>

<style scoped>
.mobile-list { display: flex; flex-direction: column; gap: var(--jf-space-3); min-width: 0; }
.bucket-title {
  margin: 0 0 var(--jf-space-1);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}
.bucket { display: flex; flex-direction: column; gap: var(--jf-space-1-5); }
</style>
