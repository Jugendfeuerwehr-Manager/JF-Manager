<template>
  <div class="list-detail">
    <!-- Loading full page -->
    <div v-if="store.loading && !store.currentList" class="loading-state">
      <ProgressSpinner style="width: 48px; height: 48px" />
      <span>Lade Liste…</span>
    </div>

    <template v-else-if="store.currentList">
      <!-- ── Toolbar ──────────────────────────────────────────────────────── -->
      <div class="toolbar" :style="{ '--accent': store.currentList.color }">
        <div class="toolbar-left">
          <Button
            icon="pi pi-arrow-left"
            text
            rounded
            size="small"
            v-tooltip.bottom="'Zurück'"
            @click="$router.push({ name: 'lists' })"
          />
          <div class="title-block">
            <div class="title-row">
              <div class="color-dot" :style="{ background: store.currentList.color }"></div>
              <h1 class="list-title">{{ store.currentList.name }}</h1>
              <Button
                icon="pi pi-pencil"
                text
                rounded
                size="small"
                v-tooltip.bottom="'Bearbeiten'"
                @click="openEditDialog"
              />
            </div>
            <p v-if="store.currentList.description" class="list-description">
              {{ store.currentList.description }}
            </p>
          </div>
        </div>

        <div class="toolbar-right">
          <!-- Stats badge -->
          <div class="stats-badge">
            <span :style="{ color: store.currentList.color }" class="stats-checked">
              {{ checkedCount }}
            </span>
            <span class="stats-sep"> / </span>
            <span class="stats-total">{{ totalCount }}</span>
          </div>

          <!-- Action buttons -->
          <Button
            icon="pi pi-check-square"
            label="Alle haken"
            text
            size="small"
            v-tooltip.bottom="'Alle als anwesend markieren'"
            @click="handleCheckAll"
          />
          <Button
            icon="pi pi-stop"
            label="Zurücksetzen"
            text
            size="small"
            severity="secondary"
            v-tooltip.bottom="'Alle Abhakungen zurücksetzen'"
            @click="handleUncheckAll"
          />
          <Button
            icon="pi pi-file-pdf"
            label="PDF"
            outlined
            size="small"
            :loading="pdfLoading"
            @click="handlePdf"
          />
          <Button
            icon="pi pi-envelope"
            label="E-Mail"
            outlined
            size="small"
            @click="handleEmail"
          />
        </div>
      </div>

      <div class="accent-bar" :style="{ background: store.currentList.color }"></div>

      <!-- ── Content: add panel + checklist ─────────────────────────────── -->
      <div class="content-area">

        <!-- Add members panel -->
        <div class="add-panel">
          <h3 class="panel-title">
            <i class="pi pi-user-plus"></i>
            Mitglieder hinzufügen
          </h3>
          <div class="add-controls">
            <AutoComplete
              v-model="memberSearchText"
              :suggestions="memberSuggestions"
              placeholder="Mitglied suchen…"
              option-label="full_name"
              class="add-autocomplete"
              :pt="{ input: { class: 'w-full' } }"
              @complete="searchMembers"
              @option-select="onMemberSelect"
              @keydown.enter="onAutoCompleteEnter"
            />
            <div class="add-buttons">
              <Button
                label="Alle hinzufügen"
                icon="pi pi-users"
                outlined
                size="small"
                @click="addAllMembers"
              />
            </div>
          </div>
          <!-- Filter chips for quick bulk-add by group -->
          <div v-if="availableGroups.length" class="group-chips">
            <span class="chips-label">Gruppe hinzufügen:</span>
            <Button
              v-for="group in availableGroups"
              :key="group.id"
              :label="group.name"
              size="small"
              text
              rounded
              @click="addGroup(group.id)"
            />
          </div>
        </div>

        <!-- Checklist -->
        <div class="checklist-section">
          <!-- Checklist toolbar: search + filter -->
          <div class="checklist-controls">
            <IconField>
              <InputIcon class="pi pi-search" />
              <InputText
                v-model="listSearch"
                placeholder="Mitglied suchen…"
                class="list-search"
                @input="onListSearchInput"
              />
            </IconField>

            <SelectButton
              v-model="filterMode"
              :options="filterOptions"
              option-label="label"
              option-value="value"
              :allow-empty="false"
              class="filter-select"
            />
          </div>

          <!-- Empty state inside list -->
          <div v-if="filteredEntries.length === 0" class="inner-empty">
            <i class="pi pi-users empty-icon"></i>
            <span>
              {{ store.currentList.entries.length === 0
                ? 'Noch keine Mitglieder in dieser Liste'
                : 'Keine Ergebnisse für diese Filter' }}
            </span>
          </div>

          <!-- Entry rows -->
          <TransitionGroup v-else name="entry-list" tag="div" class="entry-list">
            <div
              v-for="entry in filteredEntries"
              :key="entry.member.id"
              class="entry-row"
              :class="{ 'entry-row--checked': entry.checked }"
              @click="store.toggleCheck(store.currentList!.id, entry.member.id)"
            >
              <!-- Checkbox visual -->
              <div
                class="entry-check"
                :style="entry.checked ? { background: store.currentList!.color, borderColor: store.currentList!.color } : {}"
              >
                <i v-if="entry.checked" class="pi pi-check check-icon"></i>
              </div>

              <!-- Avatar -->
              <Avatar
                :image="entry.member.avatar_url ?? undefined"
                :label="initials(entry.member)"
                shape="circle"
                size="normal"
                class="entry-avatar"
              />

              <!-- Info -->
              <div class="entry-info">
                <span class="entry-name">{{ entry.member.full_name }}</span>
                <div class="entry-meta">
                  <Tag
                    v-if="entry.member.status"
                    :value="entry.member.status.name"
                    class="status-tag"
                    :style="statusStyle(entry.member)"
                  />
                  <span v-if="entry.member.group" class="group-badge">
                    <i class="pi pi-tag" style="font-size: 0.65rem"></i>
                    {{ entry.member.group.name }}
                  </span>
                </div>
              </div>

              <!-- Notes inline input -->
              <div @click.stop @keydown.stop>
                <InputText
                  v-model="localNotes[entry.member.id]"
                  placeholder="Notiz…"
                  class="notes-input"
                  size="small"
                  @blur="saveNotes(entry.member.id)"
                  @keydown.enter="saveNotes(entry.member.id)"
                />
              </div>

              <!-- Remove button -->
              <Button
                icon="pi pi-times"
                text
                rounded
                size="small"
                severity="danger"
                class="remove-btn"
                v-tooltip.top="'Aus Liste entfernen'"
                @click.stop="removeMember(entry.member.id)"
              />
            </div>
          </TransitionGroup>
        </div>
      </div>
    </template>

    <!-- Edit dialog -->
    <Dialog
      v-model:visible="showEditDialog"
      header="Liste bearbeiten"
      modal
      :style="{ width: 'min(480px, 95vw)' }"
    >
      <div class="dialog-form">
        <div class="form-field">
          <label class="field-label">Name *</label>
          <InputText v-model="editForm.name" class="w-full" autofocus @keyup.enter="saveEdit" />
        </div>
        <div class="form-field">
          <label class="field-label">Beschreibung</label>
          <Textarea v-model="editForm.description" rows="2" class="w-full" />
        </div>
        <div class="form-field">
          <label class="field-label">Farbe</label>
          <div class="color-row">
            <div
              v-for="c in colorPresets"
              :key="c"
              class="color-swatch"
              :class="{ 'color-swatch--active': editForm.color === c }"
              :style="{ background: c }"
              @click="editForm.color = c"
            ></div>
            <input type="color" v-model="editForm.color" class="color-picker" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Abbrechen" text @click="showEditDialog = false" />
        <Button
          label="Speichern"
          icon="pi pi-check"
          :disabled="!editForm.name.trim()"
          :loading="store.saving"
          @click="saveEdit"
        />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import AutoComplete from 'primevue/autocomplete'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import { useMemberListsStore } from '@/stores/lists'
import { useMembersStore } from '@/stores/members'
import { useGroupsStore } from '@/stores/groups'
import { useListPdf } from '@/composables/useListPdf'
import type { Member } from '@/types/members'

// ── Route & stores ────────────────────────────────────────────────────────
const route = useRoute()
const router = useRouter()
const toast = useToast()
const store = useMemberListsStore()
const membersStore = useMembersStore()
const groupsStore = useGroupsStore()
const { generateChecklist } = useListPdf()

const listId = computed(() => Number(route.params.id))

// ── Derived counts ────────────────────────────────────────────────────────
const checkedCount = computed(() => store.currentList?.entries.filter((e) => e.checked).length ?? 0)
const totalCount = computed(() => store.currentList?.entries.length ?? 0)

// ── Groups for quick bulk-add ─────────────────────────────────────────────
const availableGroups = computed(() => groupsStore.groups)

// ── Checklist filter / search ─────────────────────────────────────────────
const listSearch = ref('')
const filterMode = ref<'all' | 'checked' | 'unchecked'>('all')

const filterOptions = [
  { label: 'Alle', value: 'all' },
  { label: 'Anwesend', value: 'checked' },
  { label: 'Fehlend', value: 'unchecked' },
]

let searchDebounce: ReturnType<typeof setTimeout> | undefined
function onListSearchInput() {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {}, 0) // triggers reactivity
}

const filteredEntries = computed(() => {
  if (!store.currentList) return []
  let result = store.currentList.entries
  if (listSearch.value) {
    const q = listSearch.value.toLowerCase()
    result = result.filter((e) => e.member.full_name?.toLowerCase().includes(q))
  }
  if (filterMode.value === 'checked') result = result.filter((e) => e.checked)
  if (filterMode.value === 'unchecked') result = result.filter((e) => !e.checked)
  return result
})

// ── Add members autocomplete ──────────────────────────────────────────────
const memberSearchText = ref('')
const memberSuggestions = ref<Member[]>([])
const addingMember = ref(false)

function searchMembers(event: { query: string }) {
  const q = event.query.toLowerCase()
  const alreadyIds = new Set(store.currentList?.entries.map((e) => e.member.id) ?? [])
  memberSuggestions.value = membersStore.members
    .filter((m) => !alreadyIds.has(m.id) && m.full_name?.toLowerCase().includes(q))
    .slice(0, 20)
}

async function onMemberSelect(event: { value: Member }) {
  if (addingMember.value) return
  addingMember.value = true
  memberSearchText.value = ''
  memberSuggestions.value = []
  try {
    await store.addMember(listId.value, event.value.id)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht hinzugefügt werden.', life: 3000 })
  } finally {
    addingMember.value = false
  }
}

async function onAutoCompleteEnter() {
  const single = memberSuggestions.value[0]
  if (memberSuggestions.value.length === 1 && single) {
    await onMemberSelect({ value: single })
  }
}

async function addAllMembers() {
  const alreadyIds = new Set(store.currentList?.entries.map((e) => e.member.id) ?? [])
  const toAdd = membersStore.members.filter((m) => !alreadyIds.has(m.id)).map((m) => m.id)
  if (toAdd.length === 0) {
    toast.add({ severity: 'info', summary: 'Alle bereits in Liste', life: 2000 })
    return
  }
  await store.bulkAdd(listId.value, toAdd)
  toast.add({ severity: 'success', summary: `${toAdd.length} Mitglieder hinzugefügt`, life: 2500 })
}

async function addGroup(groupId: number) {
  const alreadyIds = new Set(store.currentList?.entries.map((e) => e.member.id) ?? [])
  const toAdd = membersStore.members
    .filter((m) => !alreadyIds.has(m.id) && m.group?.id === groupId)
    .map((m) => m.id)
  if (toAdd.length === 0) {
    toast.add({ severity: 'info', summary: 'Alle Mitglieder der Gruppe sind bereits in der Liste', life: 2500 })
    return
  }
  await store.bulkAdd(listId.value, toAdd)
  toast.add({ severity: 'success', summary: `${toAdd.length} Mitglieder hinzugefügt`, life: 2500 })
}

// ── Remove member ─────────────────────────────────────────────────────────
async function removeMember(memberId: number) {
  try {
    await store.removeMember(listId.value, memberId)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht entfernt werden.', life: 3000 })
  }
}

// ── Notes local state (prevents value reset on re-render) ───────────────
const localNotes = reactive<Record<number, string>>({})

watch(
  () => store.currentList?.entries,
  (entries) => {
    entries?.forEach((e) => {
      if (localNotes[e.member.id] === undefined) {
        localNotes[e.member.id] = e.notes ?? ''
      }
    })
  },
  { immediate: true, deep: false },
)

async function saveNotes(memberId: number) {
  await store.updateEntryNotes(listId.value, memberId, localNotes[memberId] ?? '')
}

// ── Check all / uncheck all ───────────────────────────────────────────────
async function handleCheckAll() {
  await store.checkAll(listId.value)
}

async function handleUncheckAll() {
  await store.uncheckAll(listId.value)
}

// ── PDF ───────────────────────────────────────────────────────────────────
const pdfLoading = ref(false)

async function handlePdf() {
  if (!store.currentList) return
  pdfLoading.value = true
  try {
    await generateChecklist(store.currentList)
  } finally {
    pdfLoading.value = false
  }
}

// ── Email ─────────────────────────────────────────────────────────────────
function handleEmail() {
  if (!store.currentList) return
  const memberIds = store.currentList.entries.map((e) => e.member.id)
  router.push({
    name: 'emails-compose',
    state: { preselectedMemberIds: memberIds, preselectSource: store.currentList.name },
  })
}

// ── Edit dialog ───────────────────────────────────────────────────────────
const showEditDialog = ref(false)
const editForm = reactive({ name: '', description: '', color: '#3B82F6' })
const colorPresets = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
  '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16',
]

function openEditDialog() {
  if (!store.currentList) return
  editForm.name = store.currentList.name
  editForm.description = store.currentList.description
  editForm.color = store.currentList.color
  showEditDialog.value = true
}

async function saveEdit() {
  if (!editForm.name.trim() || !store.currentList) return
  try {
    await store.updateList(store.currentList.id, { ...editForm })
    showEditDialog.value = false
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht gespeichert werden.', life: 4000 })
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function initials(member: Member) {
  return `${member.name?.[0] ?? ''}${member.lastname?.[0] ?? ''}`.toUpperCase() || '?'
}

function statusStyle(member: Member) {
  if (!member.status?.color) return {}
  const c = member.status.color
  return { background: `${c}22`, color: c, border: `1px solid ${c}55`, fontSize: '0.65rem' }
}

// ── Init ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    store.fetchList(listId.value),
    membersStore.fetchMembers({ limit: 1000, ordering: 'lastname,name' }),
    groupsStore.fetchGroups(),
  ])
})
</script>

<style scoped>
.list-detail {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

/* ─── Loading ─────────────────────────────────────────────────────────────── */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  flex: 1;
  color: var(--p-text-muted-color);
  padding: 4rem;
}

/* ─── Toolbar ─────────────────────────────────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem 0.75rem;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.title-block {
  flex: 1;
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.list-title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--p-text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-description {
  margin: 0.15rem 0 0;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.stats-badge {
  font-size: 1.1rem;
  font-weight: 700;
  display: flex;
  align-items: baseline;
  gap: 0.1rem;
}

.stats-checked {
  font-size: 1.4rem;
}

.stats-sep,
.stats-total {
  color: var(--p-text-muted-color);
  font-size: 1rem;
  font-weight: 400;
}

.accent-bar {
  height: 4px;
  margin: 0 1.5rem 0;
  border-radius: 99px;
}

/* ─── Content area ────────────────────────────────────────────────────────── */
.content-area {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.25rem 1.5rem;
}

/* ─── Add panel ───────────────────────────────────────────────────────────── */
.add-panel {
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-200);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.panel-title {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--p-text-color);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.add-controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.add-autocomplete {
  flex: 1;
  min-width: 200px;
}

.add-buttons {
  display: flex;
  gap: 0.5rem;
}

.group-chips {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.chips-label {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

/* ─── Checklist section ───────────────────────────────────────────────────── */
.checklist-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.checklist-controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.list-search {
  width: 220px;
}

.filter-select {
  flex-shrink: 0;
}

/* ─── Empty state inside list ─────────────────────────────────────────────── */
.inner-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 3rem 1rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.empty-icon {
  font-size: 2.5rem;
  opacity: 0.3;
}

/* ─── Entry list ──────────────────────────────────────────────────────────── */
.entry-list {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.entry-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  border: 1px solid var(--p-surface-200);
  background: var(--p-surface-0);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  user-select: none;
}

.entry-row:hover {
  background: var(--p-surface-50);
  border-color: var(--p-surface-300);
}

.entry-row--checked {
  background: color-mix(in srgb, var(--accent, #3B82F6) 6%, var(--p-surface-0));
  border-color: color-mix(in srgb, var(--accent, #3B82F6) 25%, var(--p-surface-200));
}

.entry-check {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 2px solid var(--p-surface-300);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;
}

.check-icon {
  font-size: 0.7rem;
  color: white;
  font-weight: 900;
}

.entry-avatar {
  flex-shrink: 0;
}

.entry-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.entry-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--p-text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entry-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.status-tag {
  font-size: 0.65rem !important;
  padding: 0.1rem 0.35rem !important;
  height: auto !important;
  line-height: 1.4 !important;
  border-radius: 4px !important;
}

.group-badge {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.notes-input {
  width: 160px;
  flex-shrink: 0;
}

.remove-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.entry-row:hover .remove-btn {
  opacity: 1;
}

@media (hover: none) {
  .remove-btn {
    opacity: 1;
  }
}

/* ─── Edit dialog ─────────────────────────────────────────────────────────── */
.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--p-text-color);
}

.color-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.color-swatch {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: transform 0.15s, border-color 0.15s;
  flex-shrink: 0;
}

.color-swatch:hover {
  transform: scale(1.15);
}

.color-swatch--active {
  border-color: var(--p-text-color);
  transform: scale(1.15);
}

.color-picker {
  width: 32px;
  height: 32px;
  border: none;
  padding: 0;
  border-radius: 50%;
  cursor: pointer;
  background: none;
}

/* ─── Transitions ─────────────────────────────────────────────────────────── */
.entry-list-enter-active,
.entry-list-leave-active {
  transition: all 0.2s ease;
}

.entry-list-enter-from,
.entry-list-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* ─── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 767px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    padding: 1rem;
  }

  .toolbar-right {
    width: 100%;
    justify-content: flex-start;
  }

  .content-area {
    padding: 1rem;
  }

  .notes-input {
    display: none;
  }

  .list-search {
    width: 100%;
  }
}
</style>
