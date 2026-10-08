<template>
  <section class="permission-picker" aria-label="Rechte nach Aufgabenbereichen">
    <label>Aufgaben oder Rechte suchen<input v-model="search" type="search" placeholder="Zum Beispiel Mitglieder oder Bestellungen" /></label>
    <p>Ansehen erlaubt das Lesen. „Anlegen und bearbeiten“ umfasst auch das Ansehen. Löschen und besondere Aktionen wählst du ausdrücklich dazu.</p>
    <details v-for="area in areas" :key="area.key" class="permission-area" :open="!!search.trim() || selectedCount(area.rows) > 0">
      <summary><strong>{{ area.label }}</strong><span>{{ selectedCount(area.rows) }} Rechte ausgewählt</span></summary>
      <div class="row-actions area-actions">
        <button type="button" :disabled="disabled" @click="selectArea(area.rows, false)">Alle ansehen</button>
        <button type="button" :disabled="disabled" @click="selectArea(area.rows, true)">Alle anlegen und bearbeiten</button>
      </div>
      <div v-for="row in area.rows" :key="row.key" class="permission-row">
        <strong>{{ row.label }}</strong>
        <div class="row-actions">
          <label v-for="action in row.actions" :key="action.label">
            <input type="checkbox" :aria-label="`${row.label}: ${action.label}`" :checked="allSelected(action.permissions)" :indeterminate="partlySelected(action.permissions)" :disabled="disabled" @change="toggle(action.permissions, ($event.target as HTMLInputElement).checked, action.required)" />
            {{ action.label }}<span v-if="partlySelected(action.permissions)" class="partial"> (teilweise)</span>
          </label>
        </div>
      </div>
    </details>
    <p v-if="!areas.length">Keine passenden Aufgaben gefunden.</p>
    <details class="technical"><summary>Erweiterte Ansicht · einzelne technische Rechte ({{ permissions.length }})</summary>
      <p>Hier bleiben auch zusätzliche Rechte sichtbar, für die noch keine Aufgabenbeschreibung vorhanden ist.</p>
      <label v-for="permission in permissions" :key="permission.full_codename"><input type="checkbox" :checked="modelValue.includes(permission.full_codename)" :disabled="disabled" @change="toggle([permission.full_codename], ($event.target as HTMLInputElement).checked)" /><code>{{ permission.full_codename }}</code></label>
    </details>
  </section>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { permissionLabel } from '@/utils/permissionLabels'
const props = defineProps<{ modelValue: string[]; permissions: { full_codename: string; name?: string }[]; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()
const search = ref('')
const areaLabels: Record<string, string> = { members: 'Mitglieder und Kommunikation', inventory: 'Inventar und Material', orders: 'Bestellungen', training: 'Übungen und Bibliothek', servicebook: 'Dienste und Anwesenheit', qualifications: 'Qualifikationen und Aufgaben', users: 'Benutzerkonten', auth: 'Berechtigungsverwaltung', departments: 'Abteilungen und Rollen', settings_manager: 'Einstellungen', external_sync: 'Datenabgleich', notifications: 'Benachrichtigungen' }
type Action = { label: string; permissions: string[]; required?: string[] }
type Row = { key: string; label: string; actions: Action[] }
const areas = computed(() => {
  const groups = new Map<string, { key: string; label: string; rows: Row[] }>()
  const models = new Map<string, { app: string; label: string; rights: Record<string, string> }>()
  for (const permission of props.permissions) {
    const code = permission.full_codename
    const label = permissionLabel(code)
    if (label.startsWith('Weitere Berechtigung')) continue
    const [app = '', name = ''] = code.split('.')
    if (!groups.has(app)) groups.set(app, { key: app, label: areaLabels[app] ?? 'Weitere Aufgaben', rows: [] })
    const match = /^(view|add|change|delete)_(.+)$/.exec(name)
    if (match && !label.includes('Anwendungseinstellungen')) {
      const key = `${app}.${match[2]}`
      if (!models.has(key)) models.set(key, { app, label: label.replace(/ (ansehen|anlegen|bearbeiten|löschen)$/, ''), rights: {} })
      models.get(key)!.rights[match[1]!] = code
    } else {
      groups.get(app)!.rows.push({ key: code, label, actions: [{ label: 'Erlauben', permissions: [code] }] })
    }
  }
  for (const [key, model] of models) {
    const actions: Action[] = []
    if (model.rights.view) actions.push({ label: 'Ansehen', permissions: [model.rights.view] })
    if (model.rights.add || model.rights.change) actions.push({ label: model.rights.add && model.rights.change ? 'Anlegen und bearbeiten' : model.rights.add ? 'Anlegen' : 'Bearbeiten', permissions: [model.rights.add, model.rights.change].filter((value): value is string => !!value), required: model.rights.view ? [model.rights.view] : [] })
    if (model.rights.delete) actions.push({ label: 'Löschen', permissions: [model.rights.delete] })
    groups.get(model.app)!.rows.push({ key, label: model.label, actions })
  }
  const query = search.value.toLocaleLowerCase().trim()
  return [...groups.values()].map(area => ({ ...area, rows: area.rows.filter(row => `${area.label} ${row.label} ${row.actions.map(action => action.label).join(' ')}`.toLocaleLowerCase().includes(query)).sort((a,b) => a.label.localeCompare(b.label, 'de')) })).filter(area => area.rows.length).sort((a,b) => a.label.localeCompare(b.label, 'de'))
})
function allSelected(rights: string[]) { return rights.every(right => props.modelValue.includes(right)) }
function partlySelected(rights: string[]) { return !allSelected(rights) && rights.some(right => props.modelValue.includes(right)) }
function selectedCount(rows: Row[]) { return new Set(rows.flatMap(row => row.actions.flatMap(action => [...action.permissions, ...(action.required ?? [])])).filter(right => props.modelValue.includes(right))).size }
function selectArea(rows: Row[], editing: boolean) {
  const actions = rows.flatMap(row => row.actions).filter(action => action.label === 'Ansehen' || (editing && ['Anlegen und bearbeiten', 'Anlegen', 'Bearbeiten'].includes(action.label)))
  toggle(actions.flatMap(action => [...action.permissions, ...(action.required ?? [])]), true)
}
function toggle(rights: string[], checked: boolean, required: string[] = []) {
  const selection = new Set(props.modelValue)
  for (const right of checked ? [...rights, ...required] : rights) { if (checked) selection.add(right); else selection.delete(right) }
  emit('update:modelValue', [...selection])
}
</script>
<style scoped>
.permission-picker { display: grid; gap: .75rem; }.permission-picker > label { display: grid; gap: .35rem; }
input[type="search"] { padding: .65rem; font: inherit; color: inherit; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); border-radius: .4rem; }
.permission-area { border: 1px solid var(--p-content-border-color); border-radius: .5rem; padding: .75rem; }.permission-area summary { cursor: pointer; padding: .35rem 0; }.permission-area summary span { font-size: .85rem; margin-left: .75rem; }.permission-area[open] summary { margin-bottom: .75rem; }
.permission-row { display: grid; grid-template-columns: minmax(10rem,1fr) minmax(0,2fr); gap: .5rem; padding: .65rem 0; border-top: 1px solid var(--p-content-border-color); }
.area-actions { margin-bottom: .5rem; }.area-actions button { font: inherit; padding: .45rem .6rem; border-radius: .4rem; border: 1px solid var(--p-content-border-color); color: inherit; background: var(--p-content-background); cursor: pointer; }
.row-actions { display: flex; flex-wrap: wrap; gap: .6rem 1rem; }label { display: flex; align-items: center; gap: .4rem; }input[type="checkbox"] { min-width: 1.1rem; min-height: 1.1rem; }.partial { font-size: .85rem; }
.technical { margin-top: .5rem; }.technical label { padding: .4rem 0; overflow-wrap: anywhere; }.technical code { overflow-wrap: anywhere; }
@media(max-width:600px) { .permission-row { grid-template-columns: 1fr; } }
</style>
