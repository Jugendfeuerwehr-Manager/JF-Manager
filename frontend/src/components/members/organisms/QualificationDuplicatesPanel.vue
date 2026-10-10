<template>
  <section v-if="links.duplicates.length" class="duplicates" aria-labelledby="duplicates-heading">
    <h4 id="duplicates-heading"><i class="pi pi-clone" aria-hidden="true"></i>Doppelt erfasst: am Konto und am Mitglied</h4>
    <p class="muted">
      Diese Qualifikationen stehen auch am verknüpften Verwaltungskonto. Beim Zusammenführen bleibt der Nachweis am Mitglied;
      Anhänge eines gleichen Tages werden übernommen, abweichende Einträge wandern als weiterer Nachweis zum Mitglied.
    </p>
    <ul class="rows">
      <li v-for="row in links.duplicates" :key="row.account.id">
        <label class="row">
          <Checkbox v-model="selected" :value="row.account.id" :input-id="`dup-${row.account.id}`" />
          <span class="row__text">
            <span class="row__type">{{ row.type }}</span>
            <span class="muted">Konto: {{ day(row.account.acquired) }} · Mitglied: {{ day(row.member.acquired) }}</span>
          </span>
          <StatusBadge :label="row.same_date ? 'Gleiches Datum' : 'Abweichendes Datum'" :severity="row.same_date ? 'info' : 'warning'" />
        </label>
      </li>
    </ul>
    <Message v-if="message" :severity="ok ? 'success' : 'error'" :closable="false">{{ message }}</Message>
    <Button label="Ausgewählte zusammenführen" icon="pi pi-check" :disabled="!selected.length" :loading="links.merging" @click="merge" />
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAccountLinksStore } from '@/stores/accountLinks'

const props = defineProps<{ memberId: number }>()
const emit = defineEmits<{ merged: [] }>()
const links = useAccountLinksStore()
const selected = ref<number[]>([])
const message = ref('')
const ok = ref(false)

watch(() => props.memberId, id => { selected.value = []; message.value = ''; void links.loadDuplicates(id) }, { immediate: true })

const dateFormat = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
const day = (iso: string | null) => (iso ? dateFormat.format(new Date(`${iso}T00:00:00`)) : '–')

async function merge() {
  const result = await links.mergeDuplicates(props.memberId, selected.value)
  ok.value = result.ok
  message.value = result.ok ? 'Zusammengeführt.' : (result.message ?? '')
  if (result.ok) {
    selected.value = []
    emit('merged')
  }
}
</script>

<style scoped>
.duplicates { display: flex; flex-direction: column; gap: var(--jf-space-1-5); margin-bottom: var(--jf-space-2); padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
h4 { display: flex; align-items: center; gap: var(--jf-space-1); margin: 0; font-size: var(--jf-text-md); font-weight: var(--jf-weight-semibold); }
.muted { margin: 0; color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.rows { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--jf-space-1); }
.row { display: flex; align-items: center; gap: var(--jf-space-1-5); min-height: var(--jf-touch-target); cursor: pointer; }
.row__text { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.row__type { font-weight: var(--jf-weight-semibold); }
.duplicates :deep(.p-button) { align-self: flex-start; min-height: var(--jf-touch-target); }
</style>
