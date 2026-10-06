<template>
  <main class="role-admin p-3 md:p-4">
    <header class="mb-4">
      <h1 class="text-3xl font-bold m-0">Rollenvorlagen</h1>
      <p class="text-color-secondary">Vergleiche Soll- und Ist-Rechte. Änderungen an Gruppenrechten wirken direkt auf zugewiesene Konten.</p>
    </header>

    <Message v-if="pageError" severity="error" :closable="false" class="mb-3">{{ pageError }}</Message>
    <div v-if="loading" class="flex justify-content-center p-5"><ProgressSpinner /></div>
    <Message v-else-if="!templates.length && !pageError" severity="info" :closable="false">Keine Rollenvorlagen gefunden.</Message>

    <div v-else class="role-layout">
      <Card class="role-list">
        <template #title>Vorlagen</template>
        <template #content>
          <button v-for="row in templates" :key="row.id" class="role-row" :class="{ selected: selected?.id === row.id }" @click="selectTemplate(row.id)">
            <span><strong>{{ row.name }}</strong><small>{{ row.key }} · {{ scopeName(row.scope) }}</small></span>
            <Tag v-if="row.is_archived" value="Archiviert" severity="secondary" />
          </button>
        </template>
      </Card>

      <Card v-if="selected" class="role-detail">
        <template #title>
          <div class="detail-heading"><span>{{ selected.name }}</span><Tag v-if="selected.is_archived" value="Archiviert" severity="secondary" /></div>
        </template>
        <template #content>
          <Message v-if="detailError" severity="error" :closable="false" class="mb-3">{{ detailError }}</Message>
          <div v-if="detailLoading" class="flex justify-content-center p-5"><ProgressSpinner /></div>
          <template v-else-if="comparison">
            <p class="text-color-secondary">{{ selected.key }} · {{ scopeName(selected.scope) }} · Gruppe: {{ selected.group?.name || 'nicht gebunden' }}</p>

            <section class="counts" aria-label="Zuweisungszahlen">
              <div v-for="entry in countItems" :key="entry.key"><strong>{{ comparison.assignment_counts[entry.key] }}</strong><span>{{ entry.label }}</span></div>
            </section>

            <section class="compare-grid">
              <div><h2>Fehlende Rechte <Tag :value="String(comparison.missing_permissions?.length ?? '—')" :severity="comparison.missing_permissions?.length ? 'danger' : 'success'" /></h2>
                <ul v-if="comparison.missing_permissions?.length"><li v-for="permission in comparison.missing_permissions" :key="permission"><code>{{ permission }}</code></li></ul>
                <p v-else class="text-color-secondary">Keine</p>
              </div>
              <div><h2>Zusätzliche Rechte <Tag :value="String(comparison.extra_permissions?.length ?? '—')" :severity="comparison.extra_permissions?.length ? 'warn' : 'success'" /></h2>
                <ul v-if="comparison.extra_permissions?.length"><li v-for="permission in comparison.extra_permissions" :key="permission"><code>{{ permission }}</code></li></ul>
                <p v-else class="text-color-secondary">Keine</p>
              </div>
            </section>
            <section v-if="comparison.metadata_differences && Object.keys(comparison.metadata_differences).length" class="mb-3">
              <h2>Metadaten weichen vom Katalog ab</h2>
              <ul><li v-for="(diff, field) in comparison.metadata_differences" :key="field"><code>{{ field }}</code>: {{ String(diff.actual) }} → {{ String(diff.expected) }}</li></ul>
            </section>

            <details class="mb-3"><summary>Rechte vollständig prüfen ({{ comparison.actual_permissions.length }})</summary>
              <div v-if="canChangePermissions && !selected.is_archived" class="permission-add">
                <InputText v-model="permissionToAdd" aria-label="Berechtigung hinzufügen" placeholder="app_label.codename" @keydown.enter.prevent="addPermission" />
                <Button label="Recht hinzufügen" severity="secondary" :disabled="!permissionToAdd.trim() || saving" @click="addPermission" />
              </div>
              <Message v-if="permissionError" severity="error" :closable="false">{{ permissionError }}</Message>
              <div class="permission-list"><label v-for="permission in availablePermissions" :key="permission" class="permission-option">
                <input v-model="selectedPermissions" type="checkbox" :value="permission" :disabled="!canChangePermissions || selected.is_archived" /> <code>{{ permission }}</code>
              </label></div>
              <p class="text-color-secondary">Beim Übernehmen wird die komplette Rechteauswahl ersetzt. Nicht aufgeführte Rechte werden entzogen.</p>
              <Button v-if="canChangePermissions" label="Auswahl prüfen und übernehmen" icon="pi pi-check" :disabled="selected.is_archived || !comparison.group || saving" @click="applyPermissions" />
            </details>

            <section v-if="selected.scope === 'department' && selected.is_delegable" class="mb-3">
              <h2>Delegationsfreigabe</h2>
              <p>{{ selected.delegation_approved ? 'Diese Rechteauswahl ist zur Delegation freigegeben.' : 'Keine aktuelle Freigabe. Änderungen an Rechten erfordern eine erneute Freigabe.' }}</p>
              <Button v-if="canApproveDelegation" :label="selected.delegation_approved ? 'Freigabe zurücknehmen' : 'Delegation freigeben'" :disabled="selected.is_archived || saving" @click="setDelegation" />
            </section>
            <section class="metadata-form">
              <h2>Metadaten</h2>
              <label for="role-name">Anzeigename</label><InputText id="role-name" v-model="form.name" :disabled="!canChangeMetadata || selected.is_archived" />
              <label for="role-description">Beschreibung</label><Textarea id="role-description" v-model="form.description" rows="3" :disabled="!canChangeMetadata || selected.is_archived" />
              <label class="check-line"><input v-model="form.is_delegable" type="checkbox" :disabled="!canChangeMetadata || selected.is_archived" /> Delegierbar</label>
              <Button v-if="canChangeMetadata" label="Metadaten speichern" icon="pi pi-save" :disabled="selected.is_archived || !metadataChanged" :loading="saving" @click="saveMetadata" />
            </section>

            <div class="actions">
              <Button v-if="canDuplicate" label="Vorlage kopieren" icon="pi pi-copy" severity="secondary" :disabled="selected.is_archived || !comparison.group || selected.scope === 'both' || saving" @click="openDuplicate" />
              <Button v-if="canChangeMetadata" label="Archivieren" icon="pi pi-archive" severity="danger" :disabled="selected.is_archived" :loading="saving" @click="archiveTemplate" />
            </div>
          </template>
        </template>
      </Card>
    </div>

    <Dialog v-model:visible="duplicateVisible" header="Rollenvorlage kopieren" modal :style="{ width: 'min(32rem, 95vw)' }">
      <Message v-if="duplicateError" severity="error" :closable="false">{{ duplicateError }}</Message>
      <form class="flex flex-column gap-3" @submit.prevent="duplicateTemplate">
        <label for="duplicate-key">Technischer Schlüssel</label><InputText id="duplicate-key" v-model="duplicateForm.key" required pattern="[a-z0-9_]+" />
        <label for="duplicate-name">Anzeigename</label><InputText id="duplicate-name" v-model="duplicateForm.name" required />
        <label for="duplicate-description">Beschreibung</label><Textarea id="duplicate-description" v-model="duplicateForm.description" rows="3" />
        <label class="check-line"><input v-model="duplicateForm.is_delegable" type="checkbox" /> Delegierbar</label>
        <p class="text-color-secondary">Die Rechte der Quellgruppe werden kopiert. Die neue Gruppe erhält keine Benutzer- oder Abteilungszuweisungen.</p>
        <div class="actions"><Button label="Abbrechen" severity="secondary" type="button" @click="duplicateVisible = false" /><Button label="Kopie anlegen" type="submit" :loading="saving" /></div>
      </form>
    </Dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { roleTemplatesApi } from '@/api/role-templates'
import { getApiErrorMessage } from '@/utils/apiError'
import type { RoleTemplate, RoleTemplateComparison } from '@/types/role-templates'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

const auth = useAuthStore()
const templates = ref<RoleTemplate[]>([])
const selected = ref<RoleTemplate | null>(null)
const comparison = ref<RoleTemplateComparison | null>(null)
const loading = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const pageError = ref('')
const detailError = ref('')
const duplicateError = ref('')
const duplicateVisible = ref(false)
const selectedPermissions = ref<string[]>([])
const permissionToAdd = ref('')
const permissionError = ref('')
const form = reactive({ name: '', description: '', is_delegable: false })
const duplicateForm = reactive({ key: '', name: '', description: '', is_delegable: false })

const canApproveDelegation = computed(() => auth.hasPerm('departments.can_assign_roles') && auth.hasPerm('departments.change_roletemplate'))
const canChangeMetadata = computed(() => auth.hasPerm('departments.change_roletemplate'))
const canChangePermissions = computed(() => canChangeMetadata.value && auth.hasPerm('auth.change_group'))
const canDuplicate = computed(() => auth.hasPerm('departments.add_roletemplate') && auth.hasPerm('auth.add_group'))
const metadataChanged = computed(() => !!selected.value && (form.name !== selected.value.name || form.description !== selected.value.description || form.is_delegable !== selected.value.is_delegable))
const availablePermissions = computed(() => [...new Set([...(comparison.value?.actual_permissions ?? []), ...(comparison.value?.expected_permissions ?? []), ...selectedPermissions.value])].sort())
const countItems = [
  { key: 'global_users', label: 'Konten' }, { key: 'staff_users', label: 'Staff' }, { key: 'department_roles', label: 'Abteilungsrollen' },
  { key: 'ldap_mappings', label: 'LDAP-Zuordnungen' }, { key: 'oidc_mappings', label: 'OIDC-Zuordnungen' },
] as const

function scopeName(scope: RoleTemplate['scope']) { return ({ organization: 'Organisation', department: 'Abteilung', both: 'Beide Bereiche' })[scope] }
function unwrapList(data: RoleTemplate[] | { results: RoleTemplate[] }) { return Array.isArray(data) ? data : data.results }
function addPermission() {
  const permission = permissionToAdd.value.trim()
  if (!/^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$/.test(permission)) {
    permissionError.value = 'Bitte ein Recht im Format app_label.codename eingeben.'
    return
  }
  permissionError.value = ''
  if (!selectedPermissions.value.includes(permission)) selectedPermissions.value.push(permission)
  permissionToAdd.value = ''
}
function syncForm(template: RoleTemplate) {
  form.name = template.name
  form.description = template.description
  form.is_delegable = template.is_delegable
}
async function loadTemplates(keepId?: number) {
  loading.value = true
  pageError.value = ''
  try {
    const rows: RoleTemplate[] = []
    let offset = 0
    while (true) {
      const data = (await roleTemplatesApi.list(offset)).data
      const page = unwrapList(data)
      rows.push(...page)
      if (Array.isArray(data) || !data.next || page.length === 0) break
      offset += page.length
    }
    templates.value = rows
    const nextId = keepId ?? selected.value?.id ?? templates.value[0]?.id
    if (nextId && templates.value.some((item) => item.id === nextId)) await selectTemplate(nextId)
    else { selected.value = null; comparison.value = null }
  } catch (error) {
    pageError.value = getApiErrorMessage(error, 'Rollenvorlagen konnten nicht geladen werden.')
  } finally { loading.value = false }
}
async function selectTemplate(id: number) {
  detailLoading.value = true
  detailError.value = ''
  permissionError.value = ''
  permissionToAdd.value = ''
  comparison.value = null
  try {
    const result = (await roleTemplatesApi.compare(id)).data
    comparison.value = result
    selected.value = result
    selectedPermissions.value = [...result.actual_permissions]
    syncForm(result)
  } catch (error) {
    detailError.value = getApiErrorMessage(error, 'Vergleich konnte nicht geladen werden.')
  } finally { detailLoading.value = false }
}
async function saveMetadata() {
  if (!selected.value || !comparison.value || !metadataChanged.value) return
  if (!window.confirm(`Metadaten von „${selected.value.name}“ speichern?`)) return
  saving.value = true; detailError.value = ''
  try {
    await roleTemplatesApi.update(selected.value.id, { fingerprint: comparison.value.fingerprint, ...form })
    await loadTemplates(selected.value.id)
  } catch (error) { detailError.value = getApiErrorMessage(error, 'Metadaten konnten nicht gespeichert werden. Bitte bei einem Vergleichskonflikt neu laden.') }
  finally { saving.value = false }
}
async function applyPermissions() {
  if (!selected.value || !comparison.value) return
  const effects = Object.values(comparison.value.assignment_counts).reduce((sum, count) => sum + count, 0)
  if (!window.confirm(`Die vollständige Rechteauswahl für „${selected.value.name}“ übernehmen? Das kann Rechte für bestehende Zuweisungen ändern (${effects} Zuweisungen).`)) return
  saving.value = true; detailError.value = ''
  try {
    await roleTemplatesApi.applyPermissions(selected.value.id, { fingerprint: comparison.value.fingerprint, permissions: selectedPermissions.value })
    await loadTemplates(selected.value.id)
  } catch (error) { detailError.value = getApiErrorMessage(error, 'Rechte konnten nicht übernommen werden. Bitte den Vergleich neu laden.') }
  finally { saving.value = false }
}
async function setDelegation() {
  if (!selected.value || !comparison.value) return
  const approved = !selected.value.delegation_approved
  if (!window.confirm(`${approved ? 'Delegation freigeben' : 'Freigabe zurücknehmen'} für „${selected.value.name}“ mit der angezeigten Rechteauswahl?`)) return
  saving.value = true; detailError.value = ''
  try {
    await roleTemplatesApi.delegation(selected.value.id, comparison.value.fingerprint, approved)
    await loadTemplates(selected.value.id)
  } catch (error) { detailError.value = getApiErrorMessage(error, 'Freigabe konnte nicht gespeichert werden. Bitte neu vergleichen.') }
  finally { saving.value = false }
}
async function archiveTemplate() {
  if (!selected.value || !comparison.value) return
  if (!window.confirm(`Vorlage „${selected.value.name}“ archivieren? Bestehende Gruppenrechte bleiben dabei erhalten.`)) return
  saving.value = true; detailError.value = ''
  try {
    await roleTemplatesApi.archive(selected.value.id, comparison.value.fingerprint)
    await loadTemplates(selected.value.id)
  } catch (error) { detailError.value = getApiErrorMessage(error, 'Vorlage konnte nicht archiviert werden. Bitte den Vergleich neu laden.') }
  finally { saving.value = false }
}
function openDuplicate() {
  if (!selected.value) return
  duplicateError.value = ''
  duplicateForm.key = `${selected.value.key}_copy`
  duplicateForm.name = `${selected.value.name} (Kopie)`
  duplicateForm.description = selected.value.description
  duplicateForm.is_delegable = selected.value.is_delegable
  duplicateVisible.value = true
}
async function duplicateTemplate() {
  if (!selected.value || !comparison.value) return
  if (!window.confirm(`Neue, noch nicht zugewiesene Vorlage „${duplicateForm.name}“ mit den aktuellen Rechten anlegen?`)) return
  saving.value = true; duplicateError.value = ''
  try {
    const created = (await roleTemplatesApi.duplicate(selected.value.id, { ...duplicateForm, fingerprint: comparison.value.fingerprint })).data
    duplicateVisible.value = false
    await loadTemplates(created.id)
  } catch (error) { duplicateError.value = getApiErrorMessage(error, 'Vorlage konnte nicht kopiert werden. Eingaben bleiben erhalten.') }
  finally { saving.value = false }
}
onMounted(() => { void loadTemplates() })
</script>

<style scoped>
.role-layout { display: grid; grid-template-columns: minmax(15rem, 22rem) minmax(0, 1fr); gap: 1rem; align-items: start; }
.role-row { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: .5rem; border: 0; border-bottom: 1px solid var(--surface-border); background: transparent; color: inherit; padding: .8rem .5rem; text-align: left; cursor: pointer; }
.role-row.selected { background: var(--highlight-bg); color: var(--highlight-text-color); }
.role-row span { display: grid; gap: .25rem; }.role-row small { color: var(--text-color-secondary); }
.detail-heading { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
.counts { display: grid; grid-template-columns: repeat(auto-fit, minmax(8rem,1fr)); gap: .5rem; margin: 1rem 0; }
.counts div { display: grid; padding: .75rem; border-radius: 8px; background: var(--surface-ground); }.counts strong { font-size: 1.3rem; }.counts span { color: var(--text-color-secondary); font-size: .85rem; }
.compare-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 1rem; }.compare-grid h2 { display: flex; align-items: center; gap: .5rem; }
.permission-list { max-height: 20rem; overflow: auto; display: grid; grid-template-columns: repeat(auto-fit,minmax(19rem,1fr)); gap: .35rem; margin: 1rem 0; }.permission-option { display: flex; gap: .5rem; align-items: center; overflow-wrap: anywhere; }
.permission-add { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
.metadata-form { display: grid; gap: .6rem; max-width: 42rem; margin-top: 1.5rem; }.metadata-form h2 { margin-bottom: 0; }.check-line { display: flex; align-items: center; gap: .5rem; }
.actions { display: flex; justify-content: flex-end; gap: .5rem; flex-wrap: wrap; margin-top: 1rem; }
@media(max-width: 850px) { .role-layout { grid-template-columns: 1fr; } .compare-grid { grid-template-columns: 1fr; } }
</style>
