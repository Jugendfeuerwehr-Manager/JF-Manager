<script setup lang="ts">
import Button from 'primevue/button'
import type { ChangeRequest } from '@/types/changeRequests'
import { requestDate } from '@/utils/changeRequestFields'

defineProps<{ request: ChangeRequest, busy?: boolean, error?: string | null, heading?: string }>()
const emit = defineEmits<{ edit: [], withdraw: [] }>()
</script>

<template>
  <section class="banner" :aria-labelledby="`req-title-${request.id}`">
    <div class="head">
      <i class="pi pi-clock" aria-hidden="true"></i>
      <h2 :id="`req-title-${request.id}`">{{ heading ?? 'Änderung in Prüfung' }}</h2>
    </div>
    <span class="meta">Gestellt am {{ requestDate(request.created_at) }} · wird erst nach Freigabe durch die Jugendleitung übernommen. Bis dahin gelten die bisherigen Daten.</span>
    <ul class="changes">
      <li v-for="f in request.fields" :key="f.field">
        <span class="label">{{ f.label }}</span>
        <span><s class="old"><span class="sr-only">bisher: </span>{{ f.old || '–' }}</s> → <strong><span class="sr-only">beantragt: </span>{{ f.new || '–' }}</strong></span>
      </li>
    </ul>
    <p v-if="error" class="error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i> {{ error }}</p>
    <div class="actions">
      <Button type="button" label="Antrag bearbeiten" outlined :disabled="busy" @click="emit('edit')" />
      <Button type="button" label="Zurückziehen" severity="secondary" outlined :loading="busy" :disabled="busy" @click="emit('withdraw')" />
    </div>
  </section>
</template>

<style scoped>
.banner { display: flex; flex-direction: column; gap: 10px; padding: 14px; border-radius: 14px; background: var(--p-blue-50); border: 1px solid var(--p-blue-200); color: var(--p-blue-900); }
.head { display: flex; align-items: center; gap: 8px; }
h2 { margin: 0; font-size: 15px; font-weight: 700; }
.meta { font-size: 13px; }
.changes { list-style: none; margin: 0; padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; border-radius: 10px; background: var(--p-content-background); color: var(--p-text-color); font-size: 14px; }
.changes li { display: flex; flex-direction: column; gap: 2px; overflow-wrap: anywhere; }
.label { font-size: 12px; color: var(--p-text-muted-color); }
.old { color: var(--p-text-muted-color); }
.error { margin: 0; font-size: 13px; color: var(--p-red-700); }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }
.actions :deep(.p-button) { flex: 1 1 auto; min-height: 44px; border-radius: 10px; white-space: nowrap; background: var(--p-content-background); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.app-dark .banner { background: color-mix(in srgb, var(--p-blue-400), transparent 88%); border-color: color-mix(in srgb, var(--p-blue-400), transparent 60%); color: var(--p-blue-200); }
.app-dark .error { color: var(--p-red-300); }
</style>
