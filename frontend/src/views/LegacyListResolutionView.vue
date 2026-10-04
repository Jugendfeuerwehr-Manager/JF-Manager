<template>
  <main class="resolution-page">
    <header class="page-header">
      <div>
        <h1>Altlisten klären</h1>
        <p>Ordne Inhalte ungeklärter Listen einzeln einer aktiven Abteilung zu.</p>
      </div>
      <Button label="Zurück zu Listen" icon="pi pi-arrow-left" severity="secondary" outlined @click="router.push({ name: 'lists' })" />
    </header>

    <Message v-if="!auth.user?.is_superuser" severity="error" :closable="false">
      Diese Klärungsoberfläche ist nur für Superuser verfügbar.
    </Message>
    <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-if="loading" class="loading"><ProgressSpinner /> <span>Lade offene Altlisten…</span></div>
    <Message v-else-if="auth.user?.is_superuser && !error && sources.length === 0" severity="success" :closable="false">
      Es gibt keine offenen Altlisten.
    </Message>

    <section v-for="source in sources" :key="source.id" class="source-card">
      <div class="source-heading">
        <div><h2>{{ source.name }}</h2><small>Quellliste #{{ source.id }}</small></div>
        <Tag :value="`${source.entries.length} Einträge · ${source.attachments.length} Anhänge`" severity="secondary" />
      </div>

      <Message v-if="source.description" severity="warn" :closable="false" class="description">
        <strong>Beschreibung der Quelle</strong><p>{{ source.description }}</p>
      </Message>

      <div v-if="source.targets.length" class="bindings">
        Bereits gebundene Ziele:
        <Tag v-for="target in source.targets" :key="target.department" :value="`${departmentName(target.department)} → Liste #${target.list_id}`" />
      </div>

      <div class="assignment-form">
        <label :for="`department-${source.id}`">Zielabteilung</label>
        <Select :id="`department-${source.id}`" :model-value="stateFor(source.id).department" :options="departmentOptions" option-label="name" option-value="id" placeholder="Abteilung auswählen" class="department-select" @update:model-value="loadTargets(source, $event)" />
        <small v-if="selectedTarget(source)" class="target-note">Für diese Abteilung ist Zielliste #{{ selectedTarget(source) }} fest gebunden.</small>
        <template v-else-if="stateFor(source.id).department">
          <label :for="`target-${source.id}`">Zielliste</label>
          <Select :id="`target-${source.id}`" v-model="stateFor(source.id).targetListId" :options="stateFor(source.id).targetLists" option-label="name" option-value="id" placeholder="Neue Zielliste erstellen" class="department-select" :disabled="stateFor(source.id).targetLoading || !!stateFor(source.id).targetError" />
          <small v-if="stateFor(source.id).targetLoading" class="target-note">Ziellisten werden geladen…</small>
          <small v-else-if="stateFor(source.id).targetError" class="target-error">{{ stateFor(source.id).targetError }}</small>
          <small v-else-if="stateFor(source.id).targetLists.length === 0" class="target-note">Keine bestehende Zielliste gefunden; es wird eine neue Liste erstellt.</small>
          <small v-else class="target-note">Ohne Auswahl wird eine neue Liste mit dem Quellnamen erstellt.</small>
        </template>
      </div>

      <fieldset class="content-list" :disabled="!stateFor(source.id).department || busyId === source.id">
        <legend>Mitgliedseinträge</legend>
        <p v-if="!source.entries.length" class="muted">Keine offenen Einträge.</p>
        <label v-for="entry in source.entries" :key="entry.id" class="choice-row">
          <Checkbox v-model="stateFor(source.id).entryIds" :value="entry.id" />
          <span><strong>{{ entry.member_name }}</strong> <small>#{{ entry.id }} · mögliche Abteilungen: {{ entry.department_ids.map(departmentName).join(', ') || 'keine' }}</small>
            <small v-if="entry.notes">Notiz: {{ entry.notes }}</small><small v-if="entry.checked">Bereits abgehakt</small></span>
        </label>
      </fieldset>

      <fieldset class="content-list" :disabled="!stateFor(source.id).department || busyId === source.id">
        <legend>Anhänge</legend>
        <p v-if="!source.attachments.length" class="muted">Keine offenen Anhänge.</p>
        <label v-for="attachment in source.attachments" :key="attachment.id" class="choice-row">
          <Checkbox v-model="stateFor(source.id).attachmentIds" :value="attachment.id" />
          <span><strong>{{ attachment.name || 'Datei ohne Namen' }}</strong> <small>#{{ attachment.id }} · {{ attachment.mime_type || 'Typ unbekannt' }} · {{ formatBytes(attachment.file_size) }}</small>
            <small v-if="attachment.description">{{ attachment.description }}</small></span>
        </label>
      </fieldset>

      <label v-if="source.description" class="choice-row description-choice" :class="{ disabled: !stateFor(source.id).department }">
        <Checkbox v-model="stateFor(source.id).assignDescription" binary :disabled="!stateFor(source.id).department || busyId === source.id" />
        <span><strong>Beschreibung dieser Zielliste zuordnen</strong><small>Die Beschreibung wird aus der Quelle übernommen.</small></span>
      </label>

      <Message v-if="stateFor(source.id).message" :severity="stateFor(source.id).message.startsWith('Inhalte wurden') ? 'success' : 'error'" :closable="false">{{ stateFor(source.id).message }}</Message>
      <footer class="actions">
        <Button label="Ausgewählte Inhalte zuordnen" icon="pi pi-arrow-right" :disabled="!canAssign(source)" :loading="busyId === source.id" @click="submit(source, false)" />
        <Button label="Quelle abschließen" icon="pi pi-check-circle" severity="success" outlined :disabled="!canComplete(source)" :loading="busyId === source.id" @click="submit(source, true)" />
      </footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { legacyListResolutionApi } from '@/api/legacy-list-resolution'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import { getApiErrorMessage } from '@/utils/apiError'
import type { PendingLegacyList } from '@/types/legacy-list-resolution'
import type { MemberList } from '@/types/lists'

const router = useRouter()
const auth = useAuthStore()
const departments = useDepartmentsStore()
const sources = ref<PendingLegacyList[]>([])
const departmentOptions = computed(() => departments.departments.filter((department) => department.is_active))
const loading = ref(false)
const busyId = ref<number | null>(null)
const error = ref('')
const states = reactive<Record<number, {
  department: number | null
  targetListId: number | null
  targetLists: MemberList[]
  targetLoading: boolean
  targetError: string
  entryIds: number[]
  attachmentIds: number[]
  assignDescription: boolean
  message: string
}>>({})

function stateFor(id: number) {
  if (!states[id]) states[id] = { department: null, targetListId: null, targetLists: [], targetLoading: false, targetError: '', entryIds: [], attachmentIds: [], assignDescription: false, message: '' }
  return states[id]!
}
function departmentName(id: number) { return departments.departments.find((department) => department.id === id)?.name ?? `Abteilung #${id}` }
function selectedTarget(source: PendingLegacyList) { return source.targets.find((target) => target.department === stateFor(source.id).department)?.list_id }
function canAssign(source: PendingLegacyList) {
  const state = stateFor(source.id)
  return !!state.department && !state.targetLoading && !state.targetError && (state.entryIds.length > 0 || state.attachmentIds.length > 0 || state.assignDescription)
}
function canComplete(source: PendingLegacyList) {
  const state = stateFor(source.id)
  return !!state.department && !state.targetLoading && !state.targetError && source.entries.length === 0 && source.attachments.length === 0 && !source.description.trim()
}
function formatBytes(size: number) {
  if (!size) return 'Größe unbekannt'
  return size < 1024 * 1024 ? `${Math.round(size / 1024)} KB` : `${(size / 1024 / 1024).toFixed(1)} MB`
}
async function load() {
  if (!auth.user?.is_superuser) return
  loading.value = true
  error.value = ''
  try {
    if (!departments.departments.length) await departments.fetchDepartments()
    if (departments.error) throw new Error(departments.error)
    const response = await legacyListResolutionApi.pending()
    sources.value = response.data
    for (const source of sources.value) stateFor(source.id)
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Offene Altlisten konnten nicht geladen werden. Prüfe Superuser-Zugang und Verbindung.')
  } finally { loading.value = false }
}
async function loadTargets(source: PendingLegacyList, departmentId: number | null) {
  const state = stateFor(source.id)
  state.department = departmentId
  state.targetListId = null
  state.targetLists = []
  state.targetError = ''
  state.message = ''
  if (departmentId == null) return
  state.targetLoading = true
  try {
    let page = 1
    let hasNextPage = true
    while (hasNextPage) {
      const response = await legacyListResolutionApi.targets(departmentId, page)
      state.targetLists.push(...response.data.results)
      hasNextPage = Boolean(response.data.next)
      page += 1
    }
  } catch (err) {
    state.targetError = getApiErrorMessage(err, 'Ziellisten konnten nicht geladen werden. Bitte erneut versuchen.')
  } finally { state.targetLoading = false }
}
async function submit(source: PendingLegacyList, complete: boolean) {
  const state = stateFor(source.id)
  if (!state.department) return
  if (complete && !window.confirm(`Quellliste „${source.name}“ jetzt endgültig abschließen? Danach ist keine weitere Zuordnung möglich.`)) return
  state.message = ''
  busyId.value = source.id
  try {
    const response = await legacyListResolutionApi.resolve(source.id, {
      department: state.department,
      entry_ids: state.entryIds,
      attachment_ids: state.attachmentIds,
      ...((selectedTarget(source) ?? state.targetListId) ? { target_list_id: selectedTarget(source) ?? state.targetListId! } : {}),
      assign_description: state.assignDescription,
      complete,
    })
    if (response.data.complete) {
      sources.value = sources.value.filter((item) => item.id !== source.id)
      delete states[source.id]
    } else if (response.data.pending) {
      const index = sources.value.findIndex((item) => item.id === source.id)
      if (index >= 0) sources.value[index] = response.data.pending
      state.entryIds = []
      state.attachmentIds = []
      state.assignDescription = false
      state.message = `Inhalte wurden Zielliste #${response.data.target_list_id} zugeordnet. Noch offene Inhalte können weiter zugeordnet werden.`
    }
  } catch (err) {
    state.message = getApiErrorMessage(err, 'Zuordnung fehlgeschlagen. Die Auswahl wurde beibehalten; prüfe Zielabteilung und Inhalte.')
  } finally { busyId.value = null }
}
onMounted(load)
</script>

<style scoped>
.resolution-page { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
.page-header, .source-heading, .actions { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.page-header { margin-bottom: 1.5rem; }
h1, h2, p { margin-top: 0; }
.source-card { border: 1px solid var(--surface-border); border-radius: 12px; padding: 1.25rem; margin: 1rem 0; background: var(--surface-card); }
.source-heading h2 { margin-bottom: .2rem; }
.source-heading small, .choice-row small { display: block; color: var(--text-color-secondary); margin-top: .25rem; }
.description { margin-top: 1rem; }
.description p { margin: .4rem 0 0; white-space: pre-wrap; }
.bindings { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem; margin: 1rem 0; }
.assignment-form { display: grid; gap: .5rem; margin: 1rem 0; max-width: 480px; }
.department-select { width: 100%; }
.target-note, .muted { color: var(--text-color-secondary); }
.target-error { color: var(--red-500); }
.content-list { border: 1px solid var(--surface-border); border-radius: 8px; margin: 1rem 0; padding: .75rem 1rem; }
.content-list legend { font-weight: 600; padding: 0 .35rem; }
.choice-row { display: flex; align-items: flex-start; gap: .75rem; padding: .65rem .25rem; border-top: 1px solid var(--surface-border); cursor: pointer; }
.choice-row:first-of-type { border-top: 0; }
.choice-row span { flex: 1; }
.description-choice { border: 1px solid var(--surface-border); border-radius: 8px; padding: .85rem; }
.actions { justify-content: flex-end; margin-top: 1.25rem; flex-wrap: wrap; }
.loading { display: flex; align-items: center; gap: 1rem; }
@media (max-width: 700px) { .page-header, .source-heading { align-items: flex-start; flex-direction: column; } .resolution-page { padding: 1rem; } }
</style>
