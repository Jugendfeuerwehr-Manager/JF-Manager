<template>
  <Dialog
    :visible="true"
    modal
    :header="`Konto verknüpfen: ${recordName}`"
    :closable="!store.busy"
    class="account-link-dialog"
    :style="{ width: '34rem', maxWidth: 'calc(100vw - 2rem)' }"
    @update:visible="value => { if (!value) emit('close') }"
  >
    <p class="intro">
      Wähle das Verwaltungskonto dieser Person. Die Verknüpfung wirkt erst, wenn das Konto sie bei der nächsten Anmeldung bestätigt.
    </p>

    <section v-if="store.suggestions.length" aria-labelledby="suggest-heading">
      <h3 id="suggest-heading">Vorschläge</h3>
      <ul class="candidates">
        <li v-for="c in store.suggestions" :key="`s-${c.id}`">
          <CandidateButton :candidate="c" :selected="selected === c.id" @select="selected = c.id" />
        </li>
      </ul>
    </section>

    <label class="search" for="account-search">
      <span>Konto suchen</span>
      <InputText id="account-search" v-model="query" placeholder="Name, Benutzername oder E-Mail" autocomplete="off" />
    </label>
    <p v-if="store.searching" class="muted" role="status">Suche läuft …</p>
    <ul v-else-if="store.searchResults.length" class="candidates" aria-label="Suchergebnisse">
      <li v-for="c in store.searchResults" :key="`r-${c.id}`">
        <CandidateButton :candidate="c" :selected="selected === c.id" @select="selected = c.id" />
      </li>
    </ul>
    <p v-else-if="query.trim()" class="muted">Kein passendes Konto gefunden.</p>

    <label v-if="error?.code === 'record_has_portal_account' && auth.user?.is_superuser" class="transfer">
      <Checkbox v-model="transfer" binary input-id="transfer" />
      <span>Portalzugang beenden und Verknüpfung auf dieses Konto übertragen</span>
    </label>
    <Message v-if="error" severity="error" :closable="false">{{ error.message }}</Message>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" outlined :disabled="store.busy" @click="emit('close')" />
      <Button label="Verknüpfen" icon="pi pi-link" :disabled="selected === null" :loading="store.busy" @click="submit" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { defineComponent, h, ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAccountLinksStore } from '@/stores/accountLinks'
import { useAuthStore } from '@/stores/auth'
import type { AccountCandidate, AccountLinkRecordKind, AccountLinkResult } from '@/types/accountLinks'

defineProps<{ kind: AccountLinkRecordKind, recordName: string }>()
const emit = defineEmits<{ close: [], linked: [] }>()

const store = useAccountLinksStore()
const auth = useAuthStore()
const query = ref('')
const selected = ref<number | null>(null)
const transfer = ref(false)
const error = ref<AccountLinkResult | null>(null)

void store.loadSuggestions()
store.clearSearch()

let timer: ReturnType<typeof setTimeout> | undefined
watch(query, text => {
  clearTimeout(timer)
  if (!text.trim()) { store.clearSearch(); return }
  timer = setTimeout(() => { void store.search(text) }, 250)
})

async function submit() {
  if (selected.value === null) return
  error.value = null
  const result = await store.linkAccount(selected.value, transfer.value)
  if (result.ok) emit('linked')
  else error.value = result
}

/** One selectable account; linked accounts stay visible but are marked. */
const CandidateButton = defineComponent({
  props: { candidate: { type: Object as () => AccountCandidate, required: true }, selected: Boolean },
  emits: ['select'],
  setup(p, { emit: send }) {
    const reasons = { email: 'Gleiche E-Mail-Adresse', name: 'Gleicher Name', '': '' }
    return () => h('button', {
      type: 'button',
      class: ['candidate', { 'candidate--selected': p.selected }],
      'aria-pressed': p.selected,
      onClick: () => send('select'),
    }, [
      h('i', { class: p.selected ? 'pi pi-check-circle' : 'pi pi-circle', 'aria-hidden': 'true' }),
      h('span', { class: 'candidate__text' }, [
        h('span', { class: 'candidate__name' }, p.candidate.name),
        h('span', { class: 'candidate__meta' }, [p.candidate.username, reasons[p.candidate.reason]].filter(Boolean).join(' · ')),
      ]),
      p.candidate.linked ? h(StatusBadge, { label: 'Schon verknüpft', severity: 'warning' }) : null,
    ])
  },
})
</script>

<style scoped>
.intro { margin: 0 0 var(--jf-space-2); font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
h3 { margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); }
.candidates { list-style: none; margin: 0 0 var(--jf-space-2); padding: 0; display: flex; flex-direction: column; gap: var(--jf-space-0-5); }
.search { display: flex; flex-direction: column; gap: var(--jf-space-0-5); margin-bottom: var(--jf-space-1); font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); }
.search :deep(input) { min-height: var(--jf-touch-target); }
.muted { margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.transfer { display: flex; gap: var(--jf-space-1); align-items: center; min-height: var(--jf-touch-target); font-size: var(--jf-text-sm); }
:deep(.candidate) { display: flex; align-items: center; gap: var(--jf-space-1-5); width: 100%; min-height: var(--jf-touch-target); padding: var(--jf-space-1) var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; text-align: left; cursor: pointer; }
:deep(.candidate--selected) { border-color: var(--jf-color-primary); background: var(--jf-color-selected); }
:deep(.candidate:focus-visible) { outline: var(--jf-focus-ring); outline-offset: 2px; }
:deep(.candidate__text) { display: flex; flex-direction: column; flex: 1; min-width: 0; }
:deep(.candidate__name) { font-weight: var(--jf-weight-semibold); }
:deep(.candidate__meta) { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
</style>
