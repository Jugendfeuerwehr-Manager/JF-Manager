<template>
  <section class="user-roles" aria-labelledby="user-roles-heading">
    <h3 id="user-roles-heading">Abteilungen und Rollen</h3>
    <p>Abteilung hinzufügen, Rollenvorlage auswählen und die Wirkung bestätigen. Mehrere Vorlagen pro Abteilung sind möglich.</p>
    <p v-if="store.loading" role="status">Rollen werden geladen …</p>
    <Message v-if="store.error" severity="error" :closable="false">{{ store.error }}</Message>
    <Button v-if="store.error && !store.options && !store.loading" label="Erneut laden" @click="store.load(userId)" />
    <Message v-if="store.success" severity="success" :closable="false">{{ store.success }}</Message>
    <template v-if="store.options && !store.loading">
      <p v-if="!canManage">Für dieses Konto ist keine Rollenzuweisung erlaubt. Eigene Rollen können hier nicht verändert werden.</p>
      <div v-if="canManage" class="add-department">
        <label for="add-role-department">Zur Abteilung hinzufügen</label>
        <select id="add-role-department" v-model="newDepartment" :disabled="busy">
          <option :value="null">Abteilung auswählen</option>
          <option v-for="department in remainingDepartments" :key="department.id" :value="department.id">{{ department.name }}</option>
        </select>
        <Button label="Abteilung hinzufügen" icon="pi pi-plus" :disabled="newDepartment === null || busy" @click="addDepartment" />
      </div>
      <details v-for="area in areas" :key="area.key" class="department-roles" :open="openedArea === area.key" @toggle="onToggle($event, area.key)">
        <summary>{{ area.name }} <span>{{ rows(area.id).length }} Rollen</span></summary>
        <p v-if="!rows(area.id).length">Noch keine Rolle zugewiesen. Die Zugehörigkeit wird mit der ersten gespeicherten Vorlage angelegt.</p>
        <article v-for="row in rows(area.id)" :key="`${row.template_id}:${row.role}`" class="assigned-role">
          <strong>{{ row.role }}</strong>
          <span>{{ row.sources.map(source => sourceName(source.source)).join(', ') }}</span>
          <Button v-if="canManage && row.template_id && row.sources.some(source => source.source === 'local') && isAssignable(row.template_id, area.id)" label="Lokale Rolle entfernen" severity="secondary" outlined :disabled="busy" @click="store.review({ template_id: row.template_id!, department_id: area.id, operation: 'remove' })" />
          <p v-if="row.sources.some(source => source.source !== 'local')">Externe Zuweisungen werden über LDAP/OIDC verwaltet.</p>
        </article>
        <div v-if="canManage" class="role-choice">
          <label :for="`role-template-${area.key}`">Rollenvorlage</label>
          <select :id="`role-template-${area.key}`" :value="selected[area.key] || ''" :disabled="busy" @change="choose(area.key, $event)">
            <option value="">Vorlage auswählen</option>
            <option v-for="role in availableRoles(area.id)" :key="role.id" :value="role.id">{{ role.name }}</option>
          </select>
          <p v-if="chosenRole(area)?.description">{{ chosenRole(area)?.description }}</p>
          <Button label="Vorlage zuweisen …" :disabled="!chosenRole(area) || busy" @click="store.review({ template_id: selected[area.key]!, department_id: area.id, operation: 'add' })" />
        </div>
      </details>
    </template>
    <section v-if="store.preview" class="role-preview" aria-label="Wirkung der Zuweisung">
      <h4>{{ store.preview.person.name }} · {{ store.preview.role.name }}</h4>
      <p>{{ store.preview.department?.name || 'Organisation' }} · {{ store.preview.effect }}</p>
      <p v-if="!store.preview.changed">Diese lokale Zuweisung ist bereits im gewünschten Zustand.</p>
      <p v-if="store.preview.retained_external">Eine externe Quelle erhält diese Rolle weiter aufrecht.</p>
      <h4>Hinzu kommende Rechte</h4>
      <ul v-if="store.preview.added_permissions.length"><li v-for="permission in store.preview.added_permissions" :key="permission">{{ permissionLabel(permission) }}</li></ul><p v-else>Keine</p>
      <h4>Entfallende Rechte</h4>
      <ul v-if="store.preview.removed_permissions.length"><li v-for="permission in store.preview.removed_permissions" :key="permission">{{ permissionLabel(permission) }}</li></ul><p v-else>Keine</p>
      <div class="preview-actions">
        <Button label="Abbrechen" severity="secondary" :disabled="store.saving" @click="store.discardPreview()" />
        <Button label="Rollenzuweisung speichern" :disabled="!store.preview.changed || store.saving" :loading="store.saving" @click="store.save()" />
      </div>
    </section>
  </section>
</template>
<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useUserRoleAssignmentsStore } from '@/stores/userRoleAssignments'
import { permissionLabel } from '@/utils/permissionLabels'
const props = defineProps<{ userId: number }>()
const store = useUserRoleAssignmentsStore()
const addedDepartments = ref<number[]>([])
const newDepartment = ref<number | null>(null)
const openedArea = ref('')
const selected = ref<Record<string, number>>({})
const busy = computed(() => store.saving || store.reviewing)
const canManage = computed(() => store.options?.people.some(person => person.id === props.userId) ?? false)
const rows = (id: number | null) => store.roles.filter(role => role.department_id === id)
const areas = computed(() => {
  const departments = store.options?.departments.filter(department => addedDepartments.value.includes(department.id) || rows(department.id).length) ?? []
  const result: { id: number | null; key: string; name: string }[] = departments.map(department => ({ ...department, key: String(department.id) }))
  if (store.options?.organization_allowed || rows(null).length) result.push({ id: null, key: 'organization', name: 'Organisation' })
  return result
})
const remainingDepartments = computed(() => store.options?.departments.filter(department => !areas.value.some(area => area.id === department.id)) ?? [])
const isAssignable = (template: number, id: number | null) => store.options?.roles.some(role => role.id === template && role.department_ids.includes(id)) ?? false
const availableRoles = (id: number | null) => store.options?.roles.filter(role => role.department_ids.includes(id) && !rows(id).some(row => row.template_id === role.id && row.sources.some(source => source.source === 'local'))) ?? []
const chosenRole = (area: { key: string; id: number | null }) => availableRoles(area.id).find(role => role.id === selected.value[area.key])
const sourceName = (source: string) => ({ local: 'Lokal', ldap: 'LDAP', oidc: 'OIDC' })[source as 'local']
function addDepartment() {
  if (newDepartment.value === null) return
  addedDepartments.value.push(newDepartment.value)
  openedArea.value = String(newDepartment.value)
  newDepartment.value = null
  store.discardPreview()
}
function onToggle(event: Event, key: string) {
  if ((event.target as HTMLDetailsElement).open) openedArea.value = key
}
function choose(key: string, event: Event) {
  selected.value[key] = Number((event.target as HTMLSelectElement).value)
  store.discardPreview()
}
watch(() => props.userId, id => {
  addedDepartments.value = []; selected.value = {}; newDepartment.value = null; openedArea.value = ''
  void store.load(id)
}, { immediate: true })
watch(() => store.success, success => { if (success) selected.value = {} })
onUnmounted(() => store.clear())
</script>
<style scoped>
.user-roles :deep(.p-button) { min-height: 44px; }
.user-roles { margin-top: var(--jf-space-3); padding-top: var(--jf-space-3); border-top: 1px solid var(--jf-color-border); }
.add-department, .role-choice { display: grid; gap: var(--jf-space-1); margin: var(--jf-space-2) 0; }
select { min-height: 44px; width: 100%; padding: .6rem; font: inherit; border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); color: var(--jf-color-text); background: var(--jf-color-card); }
.department-roles { border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); padding: 0 var(--jf-space-2); margin: var(--jf-space-1) 0; }
summary { min-height: 44px; padding: var(--jf-space-1) 0; cursor: pointer; font-weight: var(--jf-weight-semibold); }
summary span { color: var(--jf-color-text-muted); font-weight: normal; margin-left: var(--jf-space-1); }
.assigned-role { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); padding: var(--jf-space-1) 0; }
.assigned-role p { width: 100%; }
.role-preview { border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); padding: var(--jf-space-2); margin-top: var(--jf-space-2); }
.preview-actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
select:focus-visible, summary:focus-visible { outline: var(--jf-focus-ring); }
</style>
