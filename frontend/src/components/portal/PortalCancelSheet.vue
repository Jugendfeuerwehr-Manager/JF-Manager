<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import PortalSheet from './PortalSheet.vue'
import type { PortalPerson, PortalReason, PortalSessionItem } from '@/api/portal'
import { NOTE_MAX, REASONS, formatDay, formatDeadline, personName } from '@/utils/portalSessions'

const props = defineProps<{ item: PortalSessionItem, person: PortalPerson | null, busy?: boolean, error?: string | null }>()
const emit = defineEmits<{ close: [], submit: [payload: { reason_category: PortalReason | '', reason_note: string }] }>()

const reason = ref<PortalReason | ''>('')
const note = ref('')

const name = computed(() => personName(props.person))
const title = computed(() => (name.value ? `${name.value} abmelden` : 'Abmelden'))
const genitive = computed(() => {
  const n = name.value
  if (!n) return 'Dein'
  return /[sßxz]$/i.test(n) ? `${n}’` : `${n}s`
})
const deadline = computed(() => formatDeadline(props.item.deadlines.cancellation_closes_at))
const info = computed(() => {
  const who = name.value ?? 'dich'
  const again = deadline.value ? `Bis ${deadline.value} kannst du ${who} erneut anmelden` : `Du kannst ${who} erneut anmelden`
  if (props.item.mode === 'opt_out') {
    return deadline.value ? `Bis ${deadline.value} kannst du die Abmeldung zurücknehmen.` : 'Du kannst die Abmeldung später zurücknehmen.'
  }
  if (props.item.limited) {
    return `${genitive.value} Platz wird frei und die nächste Person auf der Warteliste rückt nach. ${again}, solange Plätze frei sind.`
  }
  return `${again}.`
})

function submit() {
  emit('submit', { reason_category: reason.value, reason_note: note.value.trim() })
}
</script>

<template>
  <PortalSheet :title="title" :subtitle="`${item.title} · ${formatDay(item.date)}`" title-id="cancel-sheet-title" @close="emit('close')">
    <fieldset class="reasons">
      <legend>Grund <span class="optional">(optional)</span></legend>
      <div class="chips">
        <label v-for="r in REASONS" :key="r.value" class="chip" :class="{ on: reason === r.value }">
          <input v-model="reason" type="radio" name="reason" :value="r.value" />{{ r.label }}
        </label>
      </div>
    </fieldset>
    <div class="note">
      <label for="cancel-note">Kurze Nachricht an die Dienstleitung <span class="optional">(optional)</span></label>
      <textarea id="cancel-note" v-model="note" rows="2" :maxlength="NOTE_MAX" aria-describedby="cancel-note-help" placeholder="z. B. Wir sind ab Freitag verreist."></textarea>
      <span id="cancel-note-help" class="help">Bitte keine Gesundheitsdetails angeben. {{ note.length }}/{{ NOTE_MAX }} Zeichen</span>
    </div>
    <div class="info"><i class="pi pi-info-circle" aria-hidden="true"></i><span>{{ info }}</span></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="buttons">
      <Button type="button" label="Abbrechen" severity="secondary" outlined :disabled="busy" @click="emit('close')" />
      <Button type="button" label="Abmeldung senden" :loading="busy" :disabled="busy" @click="submit" />
    </div>
  </PortalSheet>
</template>

<style scoped>
.reasons { border: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
legend { font-size: 14px; font-weight: 600; margin-bottom: 8px; padding: 0; }
.optional { font-weight: 400; color: var(--p-text-muted-color); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { min-height: 44px; box-sizing: border-box; padding: 0 14px; border-radius: 22px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; }
.chip input { margin: 0; accent-color: var(--p-primary-color); }
.chip.on { border: 2px solid var(--p-primary-color); background: var(--p-highlight-background); color: var(--p-highlight-color); font-weight: 600; }
.chip:focus-within { outline: 2px solid var(--p-primary-color); outline-offset: 2px; }
.note { display: flex; flex-direction: column; gap: 6px; }
.note label { font-size: 14px; font-weight: 600; }
textarea { font: inherit; font-size: 15px; padding: 10px 12px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); border-radius: 10px; resize: none; background: var(--p-form-field-background, var(--p-content-background)); color: var(--p-text-color); }
.help { font-size: 12px; color: var(--p-text-muted-color); }
.info { display: flex; gap: 8px; padding: 10px 12px; border-radius: 10px; background: var(--p-content-hover-background, var(--p-surface-50)); font-size: 13px; color: var(--p-text-muted-color); }
.info i { flex: none; margin-top: 2px; }
.error { margin: 0; font-size: 14px; color: var(--p-red-600); }
.app-dark .error { color: var(--p-red-300); }
.buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.buttons :deep(.p-button) { min-height: 48px; border-radius: 12px; }
</style>
