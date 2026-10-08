<script setup lang="ts">
import { computed, reactive } from 'vue'
import Button from 'primevue/button'
import PortalSheet from './PortalSheet.vue'
import type { ChangeRequest } from '@/types/changeRequests'
import type { RequestableField } from '@/utils/changeRequestFields'

const props = defineProps<{
  title: string
  fields: RequestableField[]
  /** Stored values by API field name. */
  current: Record<string, string>
  /** Open request: the form edits it, its new values prefill the inputs. */
  existing?: ChangeRequest | null
  busy?: boolean
  error?: string | null
  fieldErrors?: Record<string, string>
}>()
const emit = defineEmits<{ close: [], submit: [fields: Record<string, string>] }>()

const requested = new Map((props.existing?.fields ?? []).map(f => [f.field, f.new]))
const values = reactive<Record<string, string>>(
  Object.fromEntries(props.fields.map(f => [f.field, requested.get(f.field) ?? props.current[f.field] ?? ''])),
)

const changed = computed(() => {
  const out: Record<string, string> = {}
  for (const f of props.fields) {
    const next = (values[f.field] ?? '').trim()
    if (next !== (props.current[f.field] ?? '').trim()) out[f.field] = next
  }
  return out
})
const errorOf = (field: string) => props.fieldErrors?.[field]
const count = computed(() => Object.keys(changed.value).length)

function submit() {
  if (count.value) emit('submit', changed.value)
}
</script>

<template>
  <PortalSheet :title="title" :subtitle="existing ? 'Du bearbeitest deinen offenen Antrag.' : undefined" title-id="change-sheet-title" @close="emit('close')">
    <div class="info">
      <i class="pi pi-info-circle" aria-hidden="true"></i>
      <span>Deine Änderung wird erst nach Freigabe durch die Jugendleitung übernommen. Bis dahin bleiben die bisherigen Daten gültig.</span>
    </div>
    <form class="form" novalidate @submit.prevent="submit">
      <div v-for="f in fields" :key="f.field" class="field" :class="{ half: f.half }">
        <label :for="`cr-${f.field}`">{{ f.label }}</label>
        <input
          :id="`cr-${f.field}`"
          v-model="values[f.field]"
          :type="f.type"
          :autocomplete="f.autocomplete"
          :inputmode="f.type === 'tel' ? 'tel' : undefined"
          :aria-invalid="errorOf(f.field) ? 'true' : undefined"
          :aria-describedby="errorOf(f.field) ? `cr-${f.field}-error` : undefined"
          :disabled="busy"
        />
        <p v-if="errorOf(f.field)" :id="`cr-${f.field}-error`" class="error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i> {{ errorOf(f.field) }}</p>
      </div>
      <p v-if="error" class="error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i> {{ error }}</p>
      <p class="help">{{ count ? `${count} ${count === 1 ? 'Feld' : 'Felder'} geändert. Nur diese werden beantragt.` : 'Ändere die Felder, die nicht mehr stimmen.' }}</p>
      <div class="buttons">
        <Button type="button" label="Abbrechen" severity="secondary" outlined :disabled="busy" @click="emit('close')" />
        <Button type="submit" :label="existing ? 'Antrag aktualisieren' : 'Änderung beantragen'" :loading="busy" :disabled="busy || !count" />
      </div>
    </form>
  </PortalSheet>
</template>

<style scoped>
.info { display: flex; gap: 8px; padding: 10px 12px; border-radius: 10px; background: var(--p-content-hover-background, var(--p-surface-50)); font-size: 13px; color: var(--p-text-muted-color); }
.info i { flex: none; margin-top: 2px; }
.form { display: flex; flex-wrap: wrap; gap: 12px; }
.field { flex: 1 1 100%; display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.field.half { flex: 1 1 calc(50% - 6px); }
label { font-size: 14px; font-weight: 600; }
input { min-height: 44px; box-sizing: border-box; font: inherit; font-size: 16px; padding: 0 12px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); border-radius: 10px; background: var(--p-form-field-background, var(--p-content-background)); color: var(--p-text-color); }
input[aria-invalid='true'] { border: 2px solid var(--p-red-600); }
.error { margin: 0; font-size: 13px; color: var(--p-red-700); flex: 1 1 100%; }
.app-dark .error { color: var(--p-red-300); }
.app-dark input[aria-invalid='true'] { border-color: var(--p-red-300); }
.help { margin: 0; flex: 1 1 100%; font-size: 12px; color: var(--p-text-muted-color); }
.buttons { flex: 1 1 100%; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.buttons :deep(.p-button) { min-height: 48px; border-radius: 12px; }
</style>
