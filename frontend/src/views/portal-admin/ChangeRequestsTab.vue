<template>
  <section aria-label="Anträge" class="requests">
    <p class="muted">Eltern und Mitglieder beantragen Änderungen an Namen und Kontaktdaten. Erst deine Freigabe übernimmt sie.</p>
    <SegmentedControl :model-value="store.scope" :options="scopes" label="Offene oder entschiedene Anträge" @update:model-value="(v: string) => store.setScope(v as 'open' | 'decided')" />
    <Message v-if="store.notice" severity="success" :closable="false" role="status">{{ store.notice }}</Message>

    <StateView v-if="store.loading && !store.list.length" kind="loading" />
    <StateView v-else-if="store.error" kind="error" :message="store.error" @retry="store.load()" />
    <StateView v-else-if="!store.list.length" kind="empty" :title="store.scope === 'open' ? 'Keine offenen Anträge' : 'Keine entschiedenen Anträge'" message="Hier erscheinen Anträge, sobald es welche gibt." />

    <div v-else class="layout">
      <nav class="list" :aria-label="store.scope === 'open' ? 'Offene Anträge' : 'Entschiedene Anträge'">
        <button v-for="r in store.list" :key="r.id" type="button" class="item" :class="{ current: r.id === store.selectedId }" :aria-current="r.id === store.selectedId ? 'true' : undefined" @click="store.select(r.id)">
          <span class="name">{{ r.person_name }}</span>
          <span class="sub">{{ r.kind === 'parent' ? 'Elternteil' : 'Mitglied' }} · {{ fieldLabels(r) }} · von {{ r.requested_by }}</span>
          <span class="sub">
            {{ r.fields.length }} {{ r.fields.length === 1 ? 'Feld' : 'Felder' }} · {{ store.scope === 'open' ? 'seit' : r.status_label + ' am' }} {{ requestDate(store.scope === 'open' ? r.created_at : r.decided_at ?? r.updated_at) }}
            <span v-if="store.scope === 'open' && conflicts(r)" class="conflict"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> {{ conflicts(r) }} {{ conflicts(r) === 1 ? 'Konflikt' : 'Konflikte' }}</span>
            <span v-if="r.own && store.scope === 'open'" class="own"><i class="pi pi-lock" aria-hidden="true"></i> eigener Antrag</span>
          </span>
        </button>
      </nav>
      <div v-if="store.selected" class="detail">
        <ChangeRequestReview :review="store.selected" :busy="store.busy" :error="store.decideError" :error-fields="store.decideFields" @decide="payload => store.decide(store.selected!, payload)" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Message from 'primevue/message'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import StateView from '@/components/common/StateView.vue'
import ChangeRequestReview from './ChangeRequestReview.vue'
import { useChangeRequestReviewsStore } from '@/stores/changeRequestReviews'
import type { Review } from '@/types/changeRequests'
import { requestDate } from '@/utils/changeRequestFields'

const store = useChangeRequestReviewsStore()
const scopes = [{ value: 'open', label: 'Offen' }, { value: 'decided', label: 'Entschieden' }]
const fieldLabels = (r: Review) => r.fields.map(f => f.label).join(', ')
const conflicts = (r: Review) => r.fields.filter(f => f.conflict).length

const route = useRoute()
// Links from the inbox and mails (cr_review) name the request: ?tab=antraege&antrag=<id>.
onMounted(async () => {
  await store.load()
  const wanted = Number(route.query.antrag)
  if (wanted && store.list.some(r => r.id === wanted)) store.select(wanted)
})
</script>

<style scoped>
.requests { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.muted { margin: 0; color: var(--p-text-muted-color); font-size: 14px; }
.requests :deep(.segmented) { align-self: flex-start; }
.layout { display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }
.list { flex: 1 1 300px; min-width: 0; display: flex; flex-direction: column; gap: 4px; padding: 8px; border-radius: 14px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
.item { text-align: left; min-height: 44px; display: flex; flex-direction: column; gap: 4px; padding: 12px; border-radius: 10px; border: 1px solid transparent; background: transparent; color: var(--p-text-color); font: inherit; cursor: pointer; }
.item.current { border: 2px solid var(--p-primary-color); background: var(--p-highlight-background); }
.name { font-size: 15px; font-weight: 650; }
.sub { font-size: 13px; color: var(--p-text-muted-color); display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; }
.conflict { color: var(--p-orange-800); font-weight: 650; display: inline-flex; gap: 4px; align-items: center; }
.own { display: inline-flex; gap: 4px; align-items: center; }
.app-dark .conflict { color: var(--p-orange-300); }
.detail { flex: 999 1 640px; min-width: 0; padding: 20px; border-radius: 14px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
@media (max-width: 480px) { .detail { padding: 12px; } }
</style>
