<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import PortalEmptyCard from '@/components/portal/PortalEmptyCard.vue'
import PortalNotice from '@/components/portal/PortalNotice.vue'
import { usePortalStore } from '@/stores/portal'

defineProps<{ icon: string, title: string, text: string }>()

const route = useRoute()
const portal = usePortalStore()
const isData = computed(() => route?.name === 'portal-data')
const person = computed(() => portal.selectedPerson)
</script>

<template>
  <div v-if="isData" class="page">
    <h1>Daten</h1>

    <section class="card" aria-labelledby="base-title">
      <div class="card-head">
        <h2 id="base-title">Name und Kontakt</h2>
        <span class="muted small">Stand heute</span>
      </div>
      <dl v-if="person">
        <div><dt>Name</dt><dd>{{ person.first_name }} {{ person.last_name }}</dd></div>
      </dl>
      <p v-else class="muted">Keine Person ausgewählt.</p>
      <Button label="Änderung beantragen (bald verfügbar)" severity="secondary" outlined disabled class="request" />
    </section>

    <PortalNotice icon="pi pi-lock">
      Anwesenheiten, Notizen und Dienstbuch sind im Portal nicht einsehbar. Welche Daten sichtbar sind, legt die Jugendfeuerwehr fest.
    </PortalNotice>
  </div>

  <div v-else class="page">
    <h1>{{ title }}</h1>
    <PortalEmptyCard :icon="icon" :title="route?.name === 'portal-sessions' ? 'Noch keine Termine' : title">
      {{ route?.name === 'portal-sessions' ? 'Sobald Dienste veröffentlicht sind, kannst du hier an- und abmelden.' : text }}
    </PortalEmptyCard>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
h1 { margin: 4px 0 0; font-size: 18px; font-weight: 700; }
h2 { margin: 0; font-size: 15px; font-weight: 700; }
.card { display: flex; flex-direction: column; gap: 10px; padding: 14px; border-radius: 14px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.muted { color: var(--p-text-muted-color); }
.small { font-size: 12px; }
dl { margin: 0; display: flex; flex-direction: column; gap: 8px; font-size: 14px; }
dl > div { display: flex; justify-content: space-between; gap: 12px; }
dt { color: var(--p-text-muted-color); }
dd { margin: 0; text-align: right; overflow-wrap: anywhere; }
.request { min-height: 44px; border-radius: 10px; }
</style>
