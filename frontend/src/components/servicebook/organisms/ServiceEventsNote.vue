<template>
  <section class="events-note" aria-label="Besondere Vorkommnisse">
    <label for="service-events">Besondere Vorkommnisse</label>
    <Textarea id="service-events" v-model="text" rows="6" auto-resize placeholder="Verletzungen, Schäden, Auffälligkeiten …" aria-describedby="service-events-hint" @blur="save" />
    <p id="service-events-hint" class="hint">Nur für Betreuende sichtbar, nie im Portal. Wird beim Verlassen des Feldes gespeichert.</p>
    <span class="status" :class="`status--${status}`" role="status">
      <i :class="icon" aria-hidden="true"></i>{{ message }}
    </span>
    <button v-if="status === 'error'" type="button" class="retry" @click="save">Erneut versuchen</button>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Textarea from 'primevue/textarea'
import { servicesApi } from '@/api/servicebook'

const props = defineProps<{ serviceId: number; events: string | null }>()
const text = ref(props.events ?? '')
const saved = ref(props.events ?? '')
const status = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
watch(() => props.events, (value) => { text.value = value ?? ''; saved.value = value ?? '' })

async function save() {
  if (text.value === saved.value && status.value !== 'error') return
  status.value = 'saving'
  try {
    await servicesApi.partialUpdate(props.serviceId, { events: text.value || undefined })
    saved.value = text.value
    status.value = 'saved'
  } catch {
    status.value = 'error'
  }
}

const icon = computed(() => ({ idle: 'pi pi-pencil', saving: 'pi pi-spin pi-spinner', saved: 'pi pi-check', error: 'pi pi-exclamation-triangle' })[status.value])
const message = computed(() => ({ idle: 'Keine ungespeicherten Änderungen', saving: 'Speichert …', saved: 'Gespeichert', error: 'Nicht gespeichert' })[status.value])
</script>

<style scoped>
.events-note { display: flex; flex-direction: column; gap: var(--jf-space-1); }
label { font-weight: var(--jf-weight-semibold); }
.hint { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.status { display: inline-flex; align-items: center; gap: 6px; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.status--saved { color: var(--p-green-800); }
.status--error { color: var(--p-red-800); font-weight: var(--jf-weight-semibold); }
.app-dark .status--saved { color: var(--p-green-300); }
.app-dark .status--error { color: var(--p-red-300); }
.retry { align-self: flex-start; min-height: 3rem; padding: 0 var(--jf-space-2); border: 1px solid var(--p-red-700); border-radius: var(--jf-radius-md); background: transparent; color: inherit; font: inherit; cursor: pointer; }
</style>
