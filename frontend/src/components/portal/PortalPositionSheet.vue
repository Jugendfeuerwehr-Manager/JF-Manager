<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import PortalSheet from './PortalSheet.vue'
import type { PortalPerson, PortalSessionItem } from '@/api/portal'
import { formatDay, personName } from '@/utils/portalSessions'

/** Choose a position (Anmeldung) or a wished position (Zuteilung, Q3); "beliebig" is the default. */
const props = defineProps<{ item: PortalSessionItem, person: PortalPerson | null, busy?: boolean, error?: string | null }>()
const emit = defineEmits<{ close: [], submit: [slot: number | null] }>()

const choice = ref<string>('any')
const assignment = computed(() => props.item.mode === 'assignment')
const name = computed(() => personName(props.person))
const title = computed(() => {
  if (assignment.value) return name.value ? `${name.value} bewerben` : 'Bewerben'
  return name.value ? `${name.value} anmelden` : 'Anmelden'
})
const positions = computed(() => props.item.positions ?? [])
const anyFree = computed(() => positions.value.some(p => p.suits && p.free > 0))

function availability(p: { free: number, max: number, suits: boolean }): string {
  if (!p.suits) return 'Voraussetzung nicht erfüllt'
  if (assignment.value) return `${p.max} ${p.max === 1 ? 'Platz' : 'Plätze'}`
  if (p.free === 0) return 'Voll – Warteliste'
  return `${p.free} von ${p.max} frei`
}

const willWait = computed(() => {
  if (assignment.value) return false
  if (choice.value === 'any') return !anyFree.value && !props.item.free_places
  const chosen = positions.value.find(p => String(p.id) === choice.value)
  return !!chosen && chosen.free === 0
})

function submit() {
  emit('submit', choice.value === 'any' ? null : Number(choice.value))
}
</script>

<template>
  <PortalSheet :title="title" :subtitle="`${item.title} · ${formatDay(item.date)}`" title-id="position-sheet-title" @close="emit('close')">
    <fieldset class="positions">
      <legend>{{ assignment ? 'Wunschposition' : 'Position' }} <span v-if="assignment" class="optional">(optional, die Dienstleitung teilt zu)</span></legend>
      <label class="option" :class="{ on: choice === 'any' }">
        <input v-model="choice" type="radio" name="position" value="any" />
        <span class="text"><strong>Beliebige passende Position</strong><span class="muted">{{ assignment ? 'Kein besonderer Wunsch' : 'Der freie Platz wird automatisch gewählt' }}</span></span>
      </label>
      <label v-for="p in positions" :key="p.id" class="option" :class="{ on: choice === String(p.id), off: !p.suits }">
        <input v-model="choice" type="radio" name="position" :value="String(p.id)" :disabled="!p.suits" />
        <span class="text"><strong>{{ p.label }}</strong><span class="muted"><i v-if="!p.suits" class="pi pi-lock" aria-hidden="true"></i> {{ availability(p) }}</span></span>
      </label>
    </fieldset>
    <div v-if="willWait" class="info" role="status"><i class="pi pi-clock" aria-hidden="true"></i><span>Alle passenden Plätze sind vergeben. Die Meldung kommt auf die Warteliste und rückt nach, sobald ein Platz frei wird.</span></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="buttons">
      <Button type="button" label="Abbrechen" severity="secondary" outlined :disabled="busy" @click="emit('close')" />
      <Button type="button" :label="assignment ? 'Bewerbung senden' : willWait ? 'Auf die Warteliste' : 'Anmelden'" :loading="busy" :disabled="busy" @click="submit" />
    </div>
  </PortalSheet>
</template>

<style scoped>
.positions { border: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
legend { font-size: 14px; font-weight: 600; margin-bottom: 8px; padding: 0; }
.optional { font-weight: 400; color: var(--p-text-muted-color); }
.option { min-height: 48px; box-sizing: border-box; padding: 8px 14px; border-radius: 12px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); display: flex; align-items: center; gap: 10px; cursor: pointer; }
.option input { margin: 0; accent-color: var(--p-primary-color); width: 1.1rem; height: 1.1rem; flex: none; }
.option.on { border: 2px solid var(--p-primary-color); background: var(--p-highlight-background); color: var(--p-highlight-color); }
.option.off { border-style: dashed; cursor: not-allowed; opacity: 0.75; }
.option:focus-within { outline: 2px solid var(--p-primary-color); outline-offset: 2px; }
.text { display: flex; flex-direction: column; gap: 2px; font-size: 14px; }
.muted { font-size: 13px; color: var(--p-text-muted-color); }
.option.on .muted { color: inherit; }
.info { display: flex; gap: 8px; padding: 10px 12px; border-radius: 10px; background: var(--p-content-hover-background, var(--p-surface-50)); font-size: 13px; color: var(--p-text-muted-color); }
.info i { flex: none; margin-top: 2px; }
.error { margin: 0; font-size: 14px; color: var(--p-red-600); }
.app-dark .error { color: var(--p-red-300); }
.buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.buttons :deep(.p-button) { min-height: 48px; border-radius: 12px; }
</style>
