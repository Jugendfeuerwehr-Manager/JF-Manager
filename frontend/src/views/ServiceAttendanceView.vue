<template>
  <div class="service-attendance">
    <header class="attendance-head">
      <router-link :to="{ name: 'servicebook' }" class="back-link"><i class="pi pi-arrow-left" aria-hidden="true"></i>Dienstbuch</router-link>
      <StateView v-if="state" :kind="state" title="Dienst konnte nicht geladen werden" @retry="load" />
      <template v-else-if="service">
        <p class="attendance-head__eyebrow">{{ dateLine }}</p>
        <h1>{{ service.topic || 'Dienst ohne Thema' }}</h1>
        <p v-if="service.place" class="attendance-head__meta">{{ service.place }}</p>
        <router-link :to="{ name: 'service-edit', params: { id: serviceId } }" class="secondary-link">
          <i class="pi pi-pencil" aria-hidden="true"></i>Dienst bearbeiten
        </router-link>
      </template>
    </header>

    <template v-if="!state">
      <div class="tabs" role="tablist" aria-label="Dienstbereiche" @keydown="onTabKey">
        <button
          v-for="t in tabs"
          :id="`tab-${t.id}`"
          :key="t.id"
          type="button"
          role="tab"
          class="tab"
          :aria-selected="tab === t.id"
          :aria-controls="`panel-${t.id}`"
          :tabindex="tab === t.id ? 0 : -1"
          @click="selectTab(t.id)"
        >{{ t.label }}</button>
      </div>

      <div :id="`panel-${tab}`" role="tabpanel" :aria-labelledby="`tab-${tab}`" class="panel" tabindex="0">
        <ServiceRegistrations
          v-if="tab === 'registrations'"
          :data="store.registrations"
          :loading="store.registrationsLoading"
          :error="store.registrationsError"
          @retry="loadRegistrations(false)"
        />
        <AttendanceManager
          v-else-if="tab === 'attendance'"
          ref="manager"
          :service-id="serviceId"
          fixed-kind="member"
          :registrations="store.registrations"
          @takeover="sheetOpen = true"
        />
        <AttendanceManager v-else-if="tab === 'staff'" :service-id="serviceId" fixed-kind="staff" />
        <ServiceEventsNote v-else-if="service" :service-id="serviceId" :events="service.events" />
      </div>
    </template>

    <ExcusedTakeoverSheet
      v-if="sheetOpen"
      :service-id="serviceId"
      @close="sheetOpen = false"
      @applied="onApplied"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { servicesApi } from '@/api/servicebook'
import type { ServiceDetail } from '@/types/servicebook'
import { classifyApiError } from '@/utils/apiError'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import AttendanceManager from '@/components/servicebook/organisms/AttendanceManager.vue'
import ServiceRegistrations from '@/components/servicebook/organisms/ServiceRegistrations.vue'
import ServiceEventsNote from '@/components/servicebook/organisms/ServiceEventsNote.vue'
import ExcusedTakeoverSheet from '@/components/servicebook/organisms/ExcusedTakeoverSheet.vue'
import { useServiceRegistrationsStore } from '@/stores/serviceRegistrations'

type TabId = 'registrations' | 'attendance' | 'staff' | 'events'
const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'registrations', label: 'Meldungen' },
  { id: 'attendance', label: 'Anwesenheit' },
  { id: 'staff', label: 'Betreuende' },
  { id: 'events', label: 'Vorkommnisse' },
]

const route = useRoute()
const router = useRouter()
const store = useServiceRegistrationsStore()
const serviceId = computed(() => Number(route.params.id))
const service = ref<ServiceDetail | null>(null)
const state = ref<'forbidden' | 'offline' | 'error' | null>(null)
const sheetOpen = ref(false)
const manager = ref<{ refresh: () => Promise<void> } | null>(null)

/** The attendance route keeps opening on "Anwesenheit"; the detail route starts at "Meldungen". */
function initialTab(): TabId {
  const q = route.query.tab
  if (typeof q === 'string' && tabs.some((t) => t.id === q)) return q as TabId
  return route.name === 'service-attendance' ? 'attendance' : 'registrations'
}
const tab = ref<TabId>(initialTab())

function selectTab(id: TabId) {
  tab.value = id
  void router.replace({ query: { ...route.query, tab: id } })
}

function onTabKey(event: KeyboardEvent) {
  const keys = ['ArrowRight', 'ArrowLeft', 'Home', 'End']
  if (!keys.includes(event.key)) return
  event.preventDefault()
  const i = tabs.findIndex((t) => t.id === tab.value)
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (i + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
  selectTab(tabs[next]!.id)
  void nextTick(() => document.getElementById(`tab-${tabs[next]!.id}`)?.focus())
}

async function load() {
  state.value = null
  try {
    service.value = (await servicesApi.get(serviceId.value)).data
  } catch (error) {
    state.value = stateForError(classifyApiError(error))
  }
}

async function loadRegistrations(quiet: boolean) {
  await store.fetchRegistrations(serviceId.value, quiet)
}

async function onApplied() {
  await Promise.all([loadRegistrations(true), manager.value?.refresh()])
}

const dateLine = computed(() => {
  if (!service.value) return ''
  const start = new Date(service.value.start)
  const end = new Date(service.value.end)
  const day = start.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })
  const time = (d: Date) => d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  return `${day} · ${time(start)}–${time(end)}`
})

let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  store.reset()
  void load()
  void loadRegistrations(false)
  // Registrations change slowly; attendance has its own 3 s sync.
  timer = setInterval(() => { if (!document.hidden && tab.value !== 'events') void loadRegistrations(true) }, 15000)
})
onUnmounted(() => clearInterval(timer))
watch(serviceId, () => { store.reset(); void load(); void loadRegistrations(false) })
</script>

<style scoped>
.service-attendance {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 880px;
  margin: 0 auto;
  min-width: 0;
}

.attendance-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.back-link,
.secondary-link {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  color: var(--jf-color-primary);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.attendance-head__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}

.attendance-head h1 {
  margin: 0;
  font-size: var(--jf-text-2xl);
  line-height: var(--jf-leading-tight);
  letter-spacing: -0.015em;
  overflow-wrap: anywhere;
}

.attendance-head__meta {
  margin: 0;
  color: var(--jf-color-text-muted);
}

.tabs {
  display: flex;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: none;
  border-bottom: 1px solid var(--jf-color-border);
}

.tab {
  min-height: 3rem;
  padding: 0 var(--jf-space-0-5);
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: var(--jf-color-text-muted);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
  flex: 1 0 auto;
  white-space: nowrap; /* whole words; the bar scrolls instead of breaking labels */
}

.tab[aria-selected='true'] {
  border-bottom-color: var(--jf-color-primary);
  color: var(--jf-color-text);
}

.panel { min-width: 0; }
.panel:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }

@media (max-width: 767px) {
  .attendance-head h1 {
    font-size: var(--jf-text-xl);
  }
  .tab { font-size: var(--jf-text-xs); }
}
</style>
