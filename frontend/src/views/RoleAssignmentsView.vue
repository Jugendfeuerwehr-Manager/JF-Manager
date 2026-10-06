<template>
  <main class="roles-view p-3 md:p-4">
    <header><h1>Rollen und Rechte</h1><p>Person auswählen, Bereich und Rolle festlegen, Wirkung prüfen und speichern.</p></header>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="success" severity="success" :closable="false">{{ success }}</Message>
    <p v-if="loading" role="status">Rollen werden geladen …</p>
    <Button v-if="error && !loading" label="Erneut laden" severity="secondary" @click="load" />
    <section v-if="!loading" class="role-card">
      <label for="role-person">Person</label>
      <select id="role-person" v-model="personId" :disabled="saving">
        <option :value="auth.user?.id">Meine Rechte</option>
        <option v-for="person in options?.people" :key="person.id" :value="person.id">{{ person.name }}</option>
      </select>
      <form v-if="options && personId !== auth.user?.id" class="assignment-form" @submit.prevent="review">
        <label for="role-area">Bereich</label>
        <select id="role-area" v-model="area" :disabled="saving" required>
          <option value="">Bereich auswählen</option><option v-if="options.organization_allowed" value="organization">Organisation</option>
          <option v-for="department in options.departments" :key="department.id" :value="String(department.id)">{{ department.name }}</option>
        </select>
        <label for="role-choice">Rolle</label>
        <select id="role-choice" v-model="templateId" :disabled="saving || !area" required>
          <option :value="null">Rolle auswählen</option><option v-for="role in availableRoles" :key="role.id" :value="role.id">{{ role.name }}</option>
        </select>
        <p v-if="chosenRole">{{ chosenRole.description }}</p>
        <Button label="Wirkung prüfen" type="submit" :disabled="!templateId || !area || saving" :loading="reviewing" />
      </form>
      <section v-if="preview" class="preview" aria-label="Wirkung der Zuweisung">
        <h2>{{ preview.person.name }} · {{ preview.role.name }}</h2>
        <p>{{ preview.department?.name || 'Organisation' }} — {{ preview.effect }}</p>
        <p v-if="!preview.changed">Diese lokale Zuweisung ist bereits im gewünschten Zustand.</p>
        <Message v-if="preview.retained_external" severity="info" :closable="false">Eine externe Quelle erhält diese Rolle weiter aufrecht.</Message>
        <h3>Hinzu kommende Rechte</h3><ul v-if="preview.added_permissions.length"><li v-for="name in preview.added_permissions" :key="name">{{ permissionLabel(name) }}</li></ul><p v-else>Keine</p>
        <h3>Entfallende Rechte</h3><ul v-if="preview.removed_permissions.length"><li v-for="name in preview.removed_permissions" :key="name">{{ permissionLabel(name) }}</li></ul><p v-else>Keine</p>
        <details><summary>Erweiterte Ansicht</summary><ul><li v-for="name in preview.permissions" :key="name"><code>{{ name }}</code></li></ul></details>
        <div class="actions"><Button label="Vorschau verwerfen" severity="secondary" :disabled="saving" @click="preview = null" /><Button label="Zuweisung speichern" :disabled="saving || !preview.changed" :loading="saving" @click="save" /></div>
      </section>
    </section>
    <section class="role-card" aria-label="Herkunft der Rechte">
      <h2>Warum darf diese Person das?</h2>
      <p v-if="!explanations.length">Keine Gruppenrechte in diesem sichtbaren Bereich.</p>
      <article v-for="row in explanations" :key="`${row.template_id}:${row.role}:${row.department_id}`" class="explanation">
        <h3>{{ row.role }}</h3><p>{{ row.department }} · {{ row.sources.map(source => sourceName(source.source)).join(', ') }}</p>
        <details><summary>Fachliche Rechte anzeigen</summary><ul><li v-for="name in row.permissions" :key="name">{{ permissionLabel(name) }}</li></ul></details>
        <details><summary>Erweiterte Ansicht</summary><ul><li v-for="name in row.permissions" :key="name"><code>{{ name }}</code></li></ul><p v-for="source in row.sources" :key="source.source + source.source_key">{{ sourceName(source.source) }} {{ source.source_key ? `· Zuordnung ${source.source_key}` : '' }}</p></details>
        <Button v-if="options && personId !== auth.user?.id && row.template_id && row.sources.some(source => source.source === 'local')" label="Lokale Zuweisung entfernen …" severity="secondary" :disabled="saving" @click="reviewRemoval(row)" />
        <p v-else-if="row.sources.some(source => source.source !== 'local')">Externe Rollen werden über die LDAP-/OIDC-Zuordnung verwaltet.</p>
      </article>
    </section>
  </main>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { roleAssignmentsApi } from '@/api/role-assignments'
import { useAuthStore } from '@/stores/auth'
import { getApiErrorMessage } from '@/utils/apiError'
import { permissionLabel } from '@/utils/permissionLabels'
import type { RoleAssignmentInput, RoleAssignmentOptions, RoleAssignmentPreview, RoleExplanation } from '@/types/role-assignments'

const auth = useAuthStore()
const options = ref<RoleAssignmentOptions | null>(null)
const personId = ref<number | undefined>(auth.user?.id)
const area = ref('')
const templateId = ref<number | null>(null)
const explanations = ref<RoleExplanation[]>([])
const preview = ref<RoleAssignmentPreview | null>(null)
const reviewedInput = ref<RoleAssignmentInput | null>(null)
const loading = ref(false), saving = ref(false), reviewing = ref(false)
const error = ref(''), success = ref('')
let explanationSequence = 0, reviewSequence = 0
const departmentId = computed(() => area.value === 'organization' ? null : Number(area.value))
const availableRoles = computed(() => options.value?.roles.filter(role => area.value && role.department_ids.includes(departmentId.value)) ?? [])
const chosenRole = computed(() => availableRoles.value.find(role => role.id === templateId.value))
const sourceName = (source: string) => ({ local: 'Lokal', ldap: 'LDAP (extern verwaltet)', oidc: 'OIDC (extern verwaltet)' })[source as 'local']
async function explain() {
  const generation = ++explanationSequence
  explanations.value = []
  try {
    const response = await roleAssignmentsApi.explain(personId.value)
    if (generation === explanationSequence) explanations.value = response.data.roles
  } catch (err) { if (generation === explanationSequence) error.value = getApiErrorMessage(err, 'Rechte konnten nicht geladen werden.') }
}
async function load() {
  loading.value = true; error.value = ''
  try { options.value = (await roleAssignmentsApi.options()).data }
  catch (err) {
    options.value = null
    if ((err as { response?: { status: number } }).response?.status !== 403) error.value = getApiErrorMessage(err, 'Zuweisungsauswahl konnte nicht geladen werden.')
  }
  await explain(); loading.value = false
}
watch(personId, () => { reviewSequence++; reviewing.value = false; preview.value = null; area.value = ''; templateId.value = null; error.value = ''; success.value = ''; void explain() })
watch(area, () => { reviewSequence++; reviewing.value = false; templateId.value = null; preview.value = null })
watch(templateId, () => { reviewSequence++; reviewing.value = false; preview.value = null })
async function reviewInput(input: RoleAssignmentInput) {
  const generation = ++reviewSequence
  reviewing.value = true; error.value = ''; success.value = ''; preview.value = null
  try {
    const response = await roleAssignmentsApi.preview(input)
    if (generation === reviewSequence) { reviewedInput.value = input; preview.value = response.data }
  } catch (err) { if (generation === reviewSequence) error.value = getApiErrorMessage(err, 'Wirkung konnte nicht geprüft werden.') }
  finally { if (generation === reviewSequence) reviewing.value = false }
}
async function review() {
  if (!personId.value || !area.value || !templateId.value) return
  await reviewInput({ user_id: personId.value, department_id: departmentId.value, template_id: templateId.value, operation: 'add' })
}
async function reviewRemoval(row: RoleExplanation) {
  if (!personId.value || !row.template_id) return
  await reviewInput({ user_id: personId.value, department_id: row.department_id, template_id: row.template_id, operation: 'remove' })
}
async function save() {
  if (!preview.value || !reviewedInput.value || !preview.value.changed) return
  if (!window.confirm(`${preview.value.person.name}: ${preview.value.role.name} in ${preview.value.department?.name || 'der Organisation'} — ${preview.value.effect} Speichern?`)) return
  saving.value = true; error.value = ''
  try {
    await roleAssignmentsApi.apply({ ...reviewedInput.value, fingerprint: preview.value.fingerprint })
    preview.value = null; success.value = 'Zuweisung gespeichert.'
    await explain()
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Zuweisung konnte nicht gespeichert werden. Bitte die Wirkung erneut prüfen.')
    // A conflict invalidates the reviewed snapshot; form selections stay intact.
    preview.value = null
  } finally { saving.value = false }
}
onBeforeRouteLeave(() => !preview.value?.changed || window.confirm('Geprüfte Zuweisung ohne Speichern verlassen?'))
onMounted(load)
</script>
<style scoped>
.roles-view { max-width: 65rem; margin: auto; }.role-card { background: var(--surface-card); border: 1px solid var(--surface-border); padding: 1.5rem; border-radius: 12px; margin: 1rem 0; }
.assignment-form { display: grid; gap: .65rem; margin-top: 1rem; }select { display: block; width: 100%; min-height: 44px; margin-top: .5rem; border: 1px solid var(--surface-border); border-radius: 6px; background: var(--surface-ground); color: var(--text-color); padding: .6rem; font: inherit; }select:focus-visible,summary:focus-visible { outline: var(--jf-focus-ring); }
.preview { margin-top: 1.5rem; padding: 1rem; border: 1px solid var(--surface-border); }.actions { display: flex; gap: .75rem; flex-wrap: wrap; margin-top: 1rem; }.explanation + .explanation { border-top: 1px solid var(--surface-border); margin-top: 1rem; padding-top: 1rem; }summary { min-height: 44px; padding: .7rem 0; cursor: pointer; }code { overflow-wrap: anywhere; }h1,h2,h3 { margin-top: 0; }@media(max-width: 600px) { .role-card { padding: 1rem; }.actions { display: grid; } }
</style>
