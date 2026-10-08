<template>
  <div class="service-attendance">
    <header class="attendance-head">
      <router-link :to="{ name: 'servicebook' }" class="back-link"><i class="pi pi-arrow-left" aria-hidden="true"></i>Dienstbuch</router-link>
      <StateView v-if="state" :kind="state" title="Dienst konnte nicht geladen werden" @retry="load" />
      <template v-else-if="service">
        <p class="attendance-head__eyebrow">{{ dateLine }}</p>
        <h1>Anwesenheit</h1>
        <p class="attendance-head__meta">{{ [service.topic, service.place].filter(Boolean).join(' · ') || 'Dienst ohne Thema' }}</p>
        <router-link :to="{ name: 'service-edit', params: { id: serviceId } }" class="secondary-link">
          <i class="pi pi-pencil" aria-hidden="true"></i>Dienst bearbeiten
        </router-link>
      </template>
    </header>

    <AttendanceManager v-if="!state" :service-id="serviceId" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { servicesApi } from '@/api/servicebook'
import type { ServiceDetail } from '@/types/servicebook'
import { classifyApiError } from '@/utils/apiError'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import AttendanceManager from '@/components/servicebook/organisms/AttendanceManager.vue'

const route = useRoute()
const serviceId = computed(() => Number(route.params.id))
const service = ref<ServiceDetail | null>(null)
const state = ref<'forbidden' | 'offline' | 'error' | null>(null)

async function load() {
  state.value = null
  try {
    service.value = (await servicesApi.get(serviceId.value)).data
  } catch (error) {
    state.value = stateForError(classifyApiError(error))
  }
}

const dateLine = computed(() => {
  if (!service.value) return ''
  const start = new Date(service.value.start)
  const end = new Date(service.value.end)
  const day = start.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })
  const time = (d: Date) => d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  return `${day} · ${time(start)}–${time(end)}`
})

onMounted(load)
</script>

<style scoped>
.service-attendance {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 880px;
  margin: 0 auto;
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
}

.attendance-head__meta {
  margin: 0;
  color: var(--jf-color-text-muted);
}

@media (max-width: 767px) {
  .attendance-head h1 {
    font-size: var(--jf-text-xl);
  }
}
</style>
