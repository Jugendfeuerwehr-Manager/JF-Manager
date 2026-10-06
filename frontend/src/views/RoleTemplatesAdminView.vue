<template>
  <main class="role-admin p-3 md:p-4">
    <header class="mb-4">
      <h1 class="text-3xl font-bold m-0">Rollenvorlagen</h1>
      <p class="text-color-secondary">Vergleiche Soll- und Ist-Rechte. Änderungen an Gruppenrechten wirken direkt auf zugewiesene Konten.</p>
      <Button v-if="canDuplicate" label="Neue Rolle" icon="pi pi-plus" @click="openCreate" />
    </header>

    <Message v-if="pageError" severity="error" :closable="false" class="mb-3">{{ pageError }}</Message>
    <div v-if="loading" class="flex justify-content-center p-5"><ProgressSpinner /></div>
    <Message v-else-if="!templates.length && !pageError" severity="info" :closable="false">Keine Rollenvorlagen gefunden.</Message>

    <div v-else class="role-layout">
      <Card class="role-list">
        <template #title>Vorlagen</template>
        <template #content>
          <button v-for="row in templates" :key="row.id" class="role-row" :class="{ selected: selected?.id === row.id }" @click="selectTemplate(row.id)">
            <span><strong>{{ row.name }}</strong><small>{{ scopeName(row.scope) }}</small></span>
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
            <p class="text-color-secondary">{{ scopeName(selected.scope) }} · {{ selected.description }}</p>

            <section class="counts" aria-label="Zuweisungszahlen">
              <div v-for="entry in countItems" :key="entry.key"><strong>{{ comparison.assignment_counts[entry.key] }}</strong><span>{{ entry.label }}</span></div>
            </section>

            <section class="compare-grid">
              <div><h2>Fehlende Rechte <Tag :value="String(comparison.missing_permissions?.length ?? '—')" :severity="comparison.missing_permissions?.length ? 'danger' : 'success'" /></h2>
                <ul v-if="comparison.missing_permissions?.length"><li v-for="permission in comparison.missing_permissions" :key="permission">{{ permissionLabel(permission) }}</li></ul>
                <p v-else class="text-color-secondary">Keine</p>
              </div>
              <div><h2>Zusätzliche Rechte <Tag :value="String(comparison.extra_permissions?.length ?? '—')" :severity="comparison.extra_permissions?.length ? 'warn' : 'success'" /></h2>
                <ul v-if="comparison.extra_permissions?.length"><li v-for="permission in comparison.extra_permissions" :key="permission">{{ permissionLabel(permission) }}</li></ul>
                <p v-else class="text-color-secondary">Keine</p>
              </div>
            </section>
            <details v-if="comparison.metadata_differences && Object.keys(comparison.metadata_differences).length" class="mb-3">
              <summary>Erweiterter Vergleich der Rollenbeschreibung</summary>
              <ul><li v-for="(diff, field) in comparison.metadata_differences" :key="field"><code>{{ field }}</code>: {{ String(diff.actual) }} → {{ String(diff.expected) }}</li></ul>
            </details>

            <section class="mb-3">
              <h2>Was darf diese Rolle?</h2>
              <p v-if="catalogLoading" role="status">Rechte werden geladen …</p>
              <PermissionPicker v-model="selectedPermissions" :permissions="editorCatalog" :disabled="!canChangePermissions || selected.is_archived || catalogLoading || saving" />
              <p>Änderungen gelten erst nach der Bestätigung. Sie wirken dann auf alle bestehenden Zuweisungen dieser Rolle.</p>
              <Button v-if="canChangePermissions" label="Auswahl prüfen und übernehmen" icon="pi pi-check" :disabled="selected.is_archived || !comparison.group || saving || catalogLoading" @click="applyPermissions" />
              <details><summary>Erweiterte Rollendaten</summary><p>{{ selected.key }} · Gruppe: {{ selected.group?.name || 'nicht gebunden' }}</p></details>
            </section>

            <section v-if="selected.scope === 'department' && selected.is_delegable" class="mb-3">
              <h2>Zuweisung durch Abteilungsleitungen</h2>
              <p>Nach deiner Freigabe dürfen berechtigte Abteilungsleitungen diese Rolle anderen Personen ihrer Abteilung geben. Sie können dadurch keine Rechte der Rolle verändern.</p>
              <p>{{ selected.delegation_approved ? 'Abteilungsleitungen dürfen diese Rolle zuweisen.' : 'Noch nicht freigegeben. Nach einer Rechteänderung musst du die Rolle erneut prüfen und freigeben.' }}</p>
              <Button v-if="canApproveDelegation" :label="selected.delegation_approved ? 'Freigabe zurücknehmen' : 'Für Abteilungsleitungen freigeben'" :disabled="selected.is_archived || saving" @click="setDelegation" />
            </section>
            <section class="metadata-form">
              <h2>Rollenbeschreibung</h2>
              <label for="role-name">Anzeigename</label><InputText id="role-name" v-model="form.name" :disabled="!canChangeMetadata || selected.is_archived" />
              <label for="role-description">Beschreibung</label><Textarea id="role-description" v-model="form.description" rows="3" :disabled="!canChangeMetadata || selected.is_archived" />
              <label class="check-line"><input :checked="selected.scope === 'department' && form.is_delegable" @change="form.is_delegable = ($event.target as HTMLInputElement).checked" type="checkbox" :disabled="!canChangeMetadata || selected.is_archived || selected.scope !== 'department'" /> Abteilungsleitungen dürfen diese Rolle nach Freigabe zuweisen</label>
              <p class="text-color-secondary">Diese Option bereitet die Rolle für die Zuweisung durch Leitungen vor. Anschließend muss die Systemadministration die konkrete Rechteauswahl freigeben. Organisationsrollen weist nur die Systemadministration zu. Rollen mit Verwaltungs-, Lösch- oder Anonymisierungsrechten können nicht für Leitungen freigegeben werden.</p>
              <Button v-if="canChangeMetadata" label="Beschreibung speichern" icon="pi pi-save" :disabled="selected.is_archived || !metadataChanged" :loading="saving" @click="saveMetadata" />
            </section>

            <div class="actions">
              <Button v-if="canDuplicate" label="Vorlage kopieren" icon="pi pi-copy" severity="secondary" :disabled="selected.is_archived || !comparison.group || selected.scope === 'both' || saving" @click="openDuplicate" />
              <Button v-if="canChangeMetadata" label="Archivieren" icon="pi pi-archive" severity="danger" :disabled="selected.is_archived" :loading="saving" @click="archiveTemplate" />
            </div>
          </template>
        </template>
      </Card>
    </div>

    <Dialog v-model:visible="duplicateVisible" :header="creating ? 'Neue Rolle anlegen' : 'Rollenvorlage kopieren'" modal :style="{ width: 'min(38rem, 95vw)' }">
      <Message v-if="duplicateError" severity="error" :closable="false">{{ duplicateError }}</Message>
      <form class="flex flex-column gap-3" @submit.prevent="duplicateTemplate">
        <label for="duplicate-name">Anzeigename</label><InputText id="duplicate-name" v-model="duplicateForm.name" required />
        <label for="duplicate-description">Beschreibung</label><Textarea id="duplicate-description" v-model="duplicateForm.description" rows="3" />
        <template v-if="creating">
          <label for="new-role-scope">Bereich</label>
          <select id="new-role-scope" v-model="newRoleScope"><option value="department">Abteilung</option><option value="organization">Organisation</option></select>
          <h2>Was darf diese Rolle?</h2>
          <p v-if="catalogLoading" role="status">Berechtigungen werden geladen …</p>
          <PermissionPicker v-model="newRolePermissions" :permissions="creationCatalog" :disabled="catalogLoading || saving" />
          <p v-if="newRoleScope === 'organization'">Organisationssicht wird automatisch ergänzt; Fachrechte bitte ausdrücklich auswählen.</p>
        </template>
        <label class="check-line"><input :checked="(creating ? newRoleScope : selected?.scope) === 'department' && duplicateForm.is_delegable" @change="duplicateForm.is_delegable = ($event.target as HTMLInputElement).checked" type="checkbox" :disabled="(creating ? newRoleScope : selected?.scope) !== 'department'" /> Abteilungsleitungen dürfen diese Rolle nach Freigabe zuweisen</label>
              <p class="text-color-secondary">Diese Option bereitet die Rolle für die Zuweisung durch Leitungen vor. Anschließend muss die Systemadministration die konkrete Rechteauswahl freigeben. Organisationsrollen weist nur die Systemadministration zu. Rollen mit Verwaltungs-, Lösch- oder Anonymisierungsrechten können nicht für Leitungen freigegeben werden.</p>
        <details><summary>Erweiterte Ansicht</summary><label for="duplicate-key">Technischer Schlüssel (optional)</label><InputText id="duplicate-key" v-model="duplicateForm.key" pattern="[a-z][a-z0-9_]+" placeholder="Wird automatisch erzeugt" /></details>
        <p class="text-color-secondary">{{ creating ? 'Die ausgewählten Rechte werden in einer neuen Gruppe angelegt.' : 'Die Rechte der Quellgruppe werden kopiert.' }} Die neue Rolle erhält keine Zuweisungen und keine Delegationsfreigabe.</p>
        <div class="actions"><Button label="Abbrechen" severity="secondary" type="button" @click="duplicateVisible = false" /><Button :label="creating ? 'Rolle anlegen' : 'Kopie anlegen'" type="submit" :loading="saving" :disabled="catalogLoading" /></div>
      </form>
    </Dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { roleTemplatesApi } from '@/api/role-templates'
import { getApiErrorMessage } from '@/utils/apiError'
import PermissionPicker from '@/components/roles/PermissionPicker.vue'
import { permissionLabel } from '@/utils/permissionLabels'
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
const creating = ref(false)
const newRoleScope = ref<'department' | 'organization'>('department')
const newRolePermissions = ref<string[]>([])
const permissionCatalog = ref<{ full_codename: string; name: string }[]>([])
const catalogLoading = ref(false)
const selectedPermissions = ref<string[]>([])
const creationCatalog = computed(() => permissionCatalog.value.filter(permission => permission.full_codename !== 'departments.can_access_all_departments'))
const editorCatalog = computed(() => {
  const catalog = new Map(permissionCatalog.value.map(permission => [permission.full_codename, permission]))
  for (const code of [...(comparison.value?.actual_permissions ?? []), ...(comparison.value?.expected_permissions ?? []), ...selectedPermissions.value]) {
    if (!catalog.has(code)) catalog.set(code, { full_codename: code, name: permissionLabel(code) })
  }
  return [...catalog.values()]
})
const form = reactive({ name: '', description: '', is_delegable: false })
const duplicateForm = reactive({ key: '', name: '', description: '', is_delegable: false })
watch(newRoleScope, scope => { if (scope === 'organization') duplicateForm.is_delegable = false })

const canApproveDelegation = computed(() => auth.hasPerm('departments.can_assign_roles') && auth.hasPerm('departments.change_roletemplate'))
const canChangeMetadata = computed(() => auth.hasPerm('departments.change_roletemplate'))
const canChangePermissions = computed(() => canChangeMetadata.value && auth.hasPerm('auth.change_group'))
const canDuplicate = computed(() => auth.hasPerm('departments.add_roletemplate') && auth.hasPerm('auth.add_group'))
const metadataChanged = computed(() => !!selected.value && (form.name !== selected.value.name || form.description !== selected.value.description || form.is_delegable !== selected.value.is_delegable))
const countItems = [
  { key: 'global_users', label: 'Konten' }, { key: 'staff_users', label: 'Staff' }, { key: 'department_roles', label: 'Abteilungsrollen' },
  { key: 'ldap_mappings', label: 'LDAP-Zuordnungen' }, { key: 'oidc_mappings', label: 'OIDC-Zuordnungen' },
] as const

function scopeName(scope: RoleTemplate['scope']) { return ({ organization: 'Organisation', department: 'Abteilung', both: 'Beide Bereiche' })[scope] }
function unwrapList(data: RoleTemplate[] | { results: RoleTemplate[] }) { return Array.isArray(data) ? data : data.results }
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
  if (!window.confirm(`Beschreibung von „${selected.value.name}“ speichern?`)) return
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
  if (!window.confirm(`${approved ? 'Für Abteilungsleitungen freigeben' : 'Freigabe zurücknehmen'} für „${selected.value.name}“ mit der angezeigten Rechteauswahl?`)) return
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
  creating.value = false
  duplicateForm.key = ''
  duplicateForm.name = `${selected.value.name} (Kopie)`
  duplicateForm.description = selected.value.description
  duplicateForm.is_delegable = selected.value.is_delegable
  duplicateVisible.value = true
}
async function openCreate() {
  creating.value = true; duplicateError.value = ''; duplicateForm.key = ''; duplicateForm.name = ''; duplicateForm.description = ''; duplicateForm.is_delegable = false
  newRoleScope.value = 'department'; newRolePermissions.value = []; duplicateVisible.value = true
  await loadPermissionCatalog()
}
async function loadPermissionCatalog() {
  catalogLoading.value = true
  try {
    const rows: typeof permissionCatalog.value = []
    let offset = 0
    while (true) {
      const data = (await roleTemplatesApi.permissions(offset)).data
      rows.push(...data.results)
      if (!data.next || !data.results.length) break
      offset += data.results.length
    }
    permissionCatalog.value = rows
  } catch (error) {
    const message = getApiErrorMessage(error, 'Berechtigungen konnten nicht geladen werden. Bestehende Rechte bleiben erhalten.')
    if (creating.value) duplicateError.value = message
    else detailError.value = message
  }
  finally { catalogLoading.value = false }
}
async function duplicateTemplate() {
  if (!creating.value && (!selected.value || !comparison.value)) return
  if (!window.confirm(`Neue, noch nicht zugewiesene Rolle „${duplicateForm.name}“ anlegen?`)) return
  saving.value = true; duplicateError.value = ''
  try {
    const input = { ...duplicateForm, key: duplicateForm.key || undefined }
    const created = creating.value
      ? (await roleTemplatesApi.create({ ...input, scope: newRoleScope.value, permissions: newRolePermissions.value })).data
      : (await roleTemplatesApi.duplicate(selected.value!.id, { ...input, fingerprint: comparison.value!.fingerprint })).data
    duplicateVisible.value = false
    await loadTemplates(created.id)
  } catch (error) { duplicateError.value = getApiErrorMessage(error, 'Vorlage konnte nicht kopiert werden. Eingaben bleiben erhalten.') }
  finally { saving.value = false }
}
onMounted(() => { void loadTemplates(); if (canChangePermissions.value || canDuplicate.value) void loadPermissionCatalog() })
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
select { min-height: 44px; padding: .5rem; font: inherit; background: var(--surface-card); color: var(--text-color); border: 1px solid var(--surface-border); }
.metadata-form { display: grid; gap: .6rem; max-width: 42rem; margin-top: 1.5rem; }.metadata-form h2 { margin-bottom: 0; }.check-line { display: flex; align-items: center; gap: .5rem; }
.actions { display: flex; justify-content: flex-end; gap: .5rem; flex-wrap: wrap; margin-top: 1rem; }
@media(max-width: 850px) { .role-layout { grid-template-columns: 1fr; } .compare-grid { grid-template-columns: 1fr; } }
</style>
