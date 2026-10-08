<template>
  <Dialog :visible="visible" modal header="Elternzugriff verlängern" :style="{ width: '30rem', maxWidth: '96vw' }" @update:visible="$emit('update:visible', $event)">
    <form v-if="target" class="form" @submit.prevent="submit">
      <p class="lead">Elternzugriff für <strong>{{ target.name }}</strong> (Elternteil: {{ target.parentName }}) verlängern.</p>
      <p v-if="target.endsOn" class="hint">Aktuell bis {{ formatDate(target.endsOn) }}. Die Verlängerung darf höchstens 12 Monate nach dem 18. Geburtstag reichen.</p>
      <label for="ext-until">Verlängern bis *</label>
      <input id="ext-until" v-model="until" type="date" required class="field" :disabled="store.busy" />
      <label for="ext-reason">Grund *</label>
      <textarea id="ext-reason" v-model="reason" rows="3" required class="field" :disabled="store.busy" placeholder="z. B. Ausbildung läuft noch bis zum Sommer"></textarea>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    </form>
    <template #footer>
      <Button label="Abbrechen" severity="secondary" outlined :disabled="store.busy" @click="$emit('update:visible', false)" />
      <Button label="Verlängern" icon="pi pi-calendar-plus" :loading="store.busy" :disabled="!until || !reason.trim()" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import { usePortalAdminStore } from '@/stores/portalAdmin'
import { formatDate } from './accessState'

export interface ExtendTarget { parent: number, parentName: string, member: number, name: string, endsOn: string | null }

const props = defineProps<{ visible: boolean, target: ExtendTarget | null }>()
const emit = defineEmits<{ 'update:visible': [value: boolean], done: [] }>()
const store = usePortalAdminStore()
const until = ref('')
const reason = ref('')
const error = ref('')

watch(() => props.visible, open => { if (open) { until.value = ''; reason.value = ''; error.value = '' } })

async function submit() {
  if (!props.target || !until.value || !reason.value.trim()) return
  error.value = ''
  const result = await store.extend({ parent: props.target.parent, member: props.target.member, until: until.value, reason: reason.value.trim() })
  if (result.ok) { emit('update:visible', false); emit('done') } else error.value = result.message ?? 'Verlängerung nicht möglich.'
}
</script>

<style scoped>
.form { display: flex; flex-direction: column; gap: var(--jf-space-1); }
.lead, .hint { margin: 0; }
.hint { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
label { font-weight: var(--jf-weight-semibold); margin-top: var(--jf-space-1); }
.field { min-height: var(--jf-touch-target); width: 100%; padding: var(--jf-space-1); border: 1px solid var(--p-form-field-border-color); border-radius: var(--jf-radius-md); background: var(--p-form-field-background); color: var(--jf-color-text); font: inherit; }
.field:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
</style>
