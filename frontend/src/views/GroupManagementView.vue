<template>
  <div class="group-mgmt">
    <OverviewHeader title="Gruppen" :subtitle="subtitle">
      <template #actions>
        <Button label="Gruppe anlegen" icon="pi pi-plus" :disabled="loadState !== null" @click="openCreateDialog" />
      </template>
    </OverviewHeader>

    <div class="board-toolbar">
      <IconField class="board-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="searchQuery"
          placeholder="Mitglieder suchen …"
          aria-label="Mitglieder in Gruppen suchen"
          class="w-full"
          @input="onSearchInput"
        />
      </IconField>
      <p class="board-hint">Mitglieder per Ziehen oder über „Gruppe wechseln“ zuordnen.</p>
    </div>

    <StateView v-if="loadState === 'loading'" kind="loading" title="Gruppen werden geladen …" />
    <StateView
      v-else-if="loadState"
      :kind="loadState"
      :title="loadState === 'forbidden' ? 'Keine Berechtigung für Gruppen' : 'Gruppen konnten nicht geladen werden'"
      :retry="loadState !== 'forbidden'"
      @retry="load"
    />

    <!-- Board -->
    <div
      v-else
      class="group-board"
      @dragover.prevent
      @dragend="onDragEnd"
    >
      <!-- "Ohne Gruppe" column -->
      <div
        class="group-column unassigned-column"
        :class="{ 'drop-target': dragOverId === UNASSIGNED_KEY }"
        @dragover.prevent="dragOverId = UNASSIGNED_KEY"
        @drop.prevent="onDrop(null)"
      >
        <div class="column-header">
          <div class="column-title-row">
            <h2 class="column-name">
              <i class="pi pi-user-minus column-icon" aria-hidden="true"></i>
              Ohne Gruppe
            </h2>
            <span class="column-count" :aria-label="memberCountLabel(filteredUnassigned.length)">{{ filteredUnassigned.length }}</span>
          </div>
        </div>

        <div class="column-body">
          <TransitionGroup name="card-list" tag="div" class="card-list">
            <MemberGroupCard
              v-for="member in filteredUnassigned"
              :key="member.id"
              :member="member"
              :groups="store.groups"
              :is-dragging="draggingMemberId === member.id"
              @dragstart="onDragStart(member, $event)"
              @dragend="onDragEnd"
              @move-to-group="moveMember(member, $event)"
            />
          </TransitionGroup>
          <div
            v-if="filteredUnassigned.length === 0"
            class="empty-state"
          >
            <i
              :class="[
                'empty-icon pi',
                searchQuery ? 'pi-search' : 'pi-check-circle',
              ]"
            ></i>
            <span>{{ searchQuery ? 'Keine Ergebnisse' : 'Alle Mitglieder zugewiesen' }}</span>
          </div>
        </div>
      </div>

      <!-- One column per group -->
      <div
        v-for="group in store.groups"
        :key="group.id"
        class="group-column"
        :class="{ 'drop-target': dragOverId === String(group.id) }"
        @dragover.prevent="dragOverId = String(group.id)"
        @drop.prevent="onDrop(group.id)"
      >
        <div class="column-header">
          <div class="column-title-row">
            <!-- View mode -->
            <template v-if="renamingId !== group.id">
              <h2 class="column-name">
                <i class="pi pi-tag column-icon" aria-hidden="true"></i>
                {{ group.name }}
              </h2>
              <span class="column-count" :aria-label="memberCountLabel(filteredGroupMembers(group.id).length)">{{ filteredGroupMembers(group.id).length }}</span>
            </template>

            <!-- Rename mode -->
            <div v-else class="rename-field">
              <InputText
                v-model="renamingName"
                class="rename-input"
                :aria-label="`Neuer Name für ${group.name}`"
                :invalid="!!renameError"
                :aria-invalid="!!renameError || undefined"
                :aria-describedby="renameError ? `rename-error-${group.id}` : undefined"
                autofocus
                @keyup.enter="saveRename(group)"
                @keyup.escape="cancelRename"
              />
              <p v-if="renameError" :id="`rename-error-${group.id}`" class="field-error">{{ renameError }}</p>
            </div>
          </div>

          <!-- Actions: view mode -->
          <div v-if="renamingId !== group.id" class="column-actions">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              severity="secondary"
              :aria-label="`Gruppe ${group.name} umbenennen`"
              v-tooltip.top="'Umbenennen'"
              @click="startRename(group)"
            />
            <Button
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              :aria-label="`Gruppe ${group.name} löschen`"
              v-tooltip.top="'Gruppe löschen'"
              @click="confirmDeleteGroup(group)"
            />
          </div>

          <!-- Actions: rename mode -->
          <div v-else class="column-actions">
            <Button
              icon="pi pi-check"
              text
              rounded
              :aria-label="`Namen für ${group.name} speichern`"
              v-tooltip.top="'Speichern'"
              :loading="store.saving"
              @click="saveRename(group)"
            />
            <Button
              icon="pi pi-times"
              text
              rounded
              severity="secondary"
              aria-label="Umbenennen abbrechen"
              v-tooltip.top="'Abbrechen'"
              @click="cancelRename"
            />
          </div>
        </div>

        <div class="column-body">
          <TransitionGroup name="card-list" tag="div" class="card-list">
            <MemberGroupCard
              v-for="member in filteredGroupMembers(group.id)"
              :key="member.id"
              :member="member"
              :groups="store.groups"
              :is-dragging="draggingMemberId === member.id"
              @dragstart="onDragStart(member, $event)"
              @dragend="onDragEnd"
              @move-to-group="moveMember(member, $event)"
            />
          </TransitionGroup>
          <div
            v-if="filteredGroupMembers(group.id).length === 0"
            class="empty-state"
          >
            <i
              :class="[
                'empty-icon pi',
                searchQuery ? 'pi-search' : 'pi-inbox',
              ]"
            ></i>
            <span>{{ searchQuery ? 'Keine Ergebnisse' : 'Noch keine Mitglieder' }}</span>
          </div>
        </div>
      </div>

      <!-- Add-group tile -->
      <button type="button" class="add-group-tile" @click="openCreateDialog">
        <i class="pi pi-plus-circle add-icon" aria-hidden="true"></i>
        <span>Gruppe anlegen</span>
      </button>
    </div>

    <!-- Create group dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      header="Gruppe anlegen"
      modal
      :style="{ width: 'min(420px, 92vw)' }"
    >
      <div class="dialog-field">
        <label for="new-group-name" class="field-label">Name der Gruppe</label>
        <InputText
          id="new-group-name"
          v-model="newGroupName"
          placeholder="z. B. Gruppe 1"
          class="w-full"
          autofocus
          :invalid="!!createError"
          :aria-invalid="!!createError || undefined"
          :aria-describedby="createError ? 'new-group-error' : undefined"
          @keyup.enter="createGroup"
        />
        <p v-if="createError" id="new-group-error" class="field-error">{{ createError }}</p>
      </div>
      <template #footer>
        <Button label="Abbrechen" text severity="secondary" @click="showCreateDialog = false" />
        <Button
          label="Gruppe anlegen"
          icon="pi pi-check"
          :disabled="!newGroupName.trim()"
          :loading="store.saving"
          @click="createGroup"
        />
      </template>
    </Dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import StateView, { stateForError, type StateKind } from '@/components/common/StateView.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import MemberGroupCard from '@/components/members/atoms/MemberGroupCard.vue'
import { useQueryTableState } from '@/composables/useQueryTableState'
import { useGroupsStore } from '@/stores/groups'
import type { Group, Member } from '@/types/members'
import { classifyApiError, getApiErrorMessage } from '@/utils/apiError'

// ─── Constants ────────────────────────────────────────────────────────────────
const UNASSIGNED_KEY = '__unassigned__'

// ─── Store / services ─────────────────────────────────────────────────────────
const store = useGroupsStore()
const confirm = useConfirm()
const toast = useToast()

// ─── Search ───────────────────────────────────────────────────────────────────
const { getString, syncToUrl } = useQueryTableState()
const searchQuery = ref(getString('search'))
let searchTimeout: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => syncToUrl({ search: searchQuery.value.trim() }), 300)
}

const memberCountLabel = (count: number) => (count === 1 ? '1 Mitglied' : `${count} Mitglieder`)

const matchesSearch = (member: Member) => {
  if (!searchQuery.value) return true
  const q = searchQuery.value.toLowerCase()
  return (
    member.full_name?.toLowerCase().includes(q) ||
    member.name?.toLowerCase().includes(q) ||
    member.lastname?.toLowerCase().includes(q)
  )
}

// ─── Derived lists ────────────────────────────────────────────────────────────
const totalMemberCount = computed(() => store.members.length)
const subtitle = computed(() => {
  if (loadState.value === 'loading') return 'Gruppen werden geladen …'
  const groups = store.groups.length
  return `${memberCountLabel(totalMemberCount.value)} · ${groups === 1 ? '1 Gruppe' : `${groups} Gruppen`}`
})

const groupExistsInBoard = (groupId: number | null | undefined) => {
  if (!groupId) return false
  return store.groups.some((group) => group.id === groupId)
}

const filteredUnassigned = computed(() =>
  store.members.filter((member) => {
    const hasUnknownGroup = member.group && !groupExistsInBoard(member.group.id)
    return (!member.group || hasUnknownGroup) && matchesSearch(member)
  }),
)

const filteredGroupMembers = (groupId: number) =>
  store.members.filter((m) => m.group?.id === groupId && matchesSearch(m))

// ─── Drag-and-drop ────────────────────────────────────────────────────────────
const draggingMemberId = ref<number | null>(null)
const dragOverId = ref<string | null>(null)

function onDragStart(member: Member, _event: DragEvent) {
  draggingMemberId.value = member.id
}

function onDragEnd() {
  draggingMemberId.value = null
  dragOverId.value = null
}

async function onDrop(targetGroupId: number | null) {
  dragOverId.value = null

  if (draggingMemberId.value === null) return

  const member = store.members.find((m) => m.id === draggingMemberId.value)
  if (!member) return

  const currentGroupId = member.group?.id ?? null
  if (currentGroupId === targetGroupId) return

  draggingMemberId.value = null
  await moveMember(member, targetGroupId)
}

// ─── Move member (shared by DnD and menu) ────────────────────────────────────
async function moveMember(member: Member, targetGroupId: number | null) {
  const targetName =
    targetGroupId === null
      ? 'Ohne Gruppe'
      : (store.groups.find((g) => g.id === targetGroupId)?.name ?? 'Gruppe')

  try {
    await store.assignMember(member.id, targetGroupId)
    toast.add({
      severity: 'success',
      summary: 'Verschoben',
      detail: `${member.full_name} → ${targetName}`,
      life: 2500,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Nicht verschoben',
      detail: `${member.full_name} bleibt in der bisherigen Gruppe.`,
      life: 4000,
    })
  }
}

// ─── Create group ─────────────────────────────────────────────────────────────
const showCreateDialog = ref(false)
const newGroupName = ref('')
const createError = ref('')

function openCreateDialog() {
  newGroupName.value = ''
  createError.value = ''
  showCreateDialog.value = true
}

async function createGroup() {
  const name = newGroupName.value.trim()
  if (!name) {
    createError.value = 'Bitte einen Namen eingeben.'
    return
  }
  createError.value = ''
  try {
    await store.createGroup(name)
    showCreateDialog.value = false
    toast.add({ severity: 'success', summary: 'Angelegt', detail: `Gruppe „${name}“ angelegt.`, life: 2500 })
  } catch (error) {
    createError.value = getApiErrorMessage(error, 'Gruppe konnte nicht angelegt werden.')
  }
}

// ─── Rename group ─────────────────────────────────────────────────────────────
const renamingId = ref<number | null>(null)
const renamingName = ref('')
const renameError = ref('')

function startRename(group: Group) {
  renamingId.value = group.id
  renamingName.value = group.name
  renameError.value = ''
}

function cancelRename() {
  renamingId.value = null
  renameError.value = ''
}

async function saveRename(group: Group) {
  if (renamingId.value !== group.id) return
  const trimmed = renamingName.value.trim()
  if (!trimmed) {
    renameError.value = 'Bitte einen Namen eingeben.'
    return
  }
  if (trimmed === group.name) {
    cancelRename()
    return
  }
  try {
    await store.updateGroup(group.id, trimmed)
    cancelRename()
  } catch (error) {
    renameError.value = getApiErrorMessage(error, 'Name konnte nicht gespeichert werden.')
  }
}

// ─── Delete group ─────────────────────────────────────────────────────────────
function confirmDeleteGroup(group: Group) {
  const count = store.members.filter((m) => m.group?.id === group.id).length
  const detail =
    count > 0
      ? `Die Gruppe „${group.name}" hat ${count} Mitglied${count === 1 ? '' : 'er'}. Diese werden keiner Gruppe mehr zugewiesen.`
      : `Gruppe „${group.name}" wirklich löschen?`

  confirm.require({
    header: 'Gruppe löschen',
    message: detail,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    acceptClass: 'p-button-danger',
    rejectLabel: 'Abbrechen',
    accept: () => deleteGroup(group),
  })
}

async function deleteGroup(group: Group) {
  try {
    await store.deleteGroup(group.id)
    toast.add({ severity: 'success', summary: 'Gelöscht', detail: `Gruppe „${group.name}" entfernt.`, life: 2500 })
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Nicht gelöscht', detail: getApiErrorMessage(error, 'Gruppe konnte nicht gelöscht werden.'), life: 5000 })
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
const loadState = ref<StateKind | null>('loading')

async function load() {
  loadState.value = 'loading'
  try {
    await Promise.all([store.fetchGroups(), store.fetchAllMembers()])
    loadState.value = null
  } catch (error) {
    loadState.value = stateForError(classifyApiError(error))
  }
}

onMounted(load)
</script>

<style scoped>
/* ─── Layout ──────────────────────────────────────────────────────────────── */
.group-mgmt {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ─── Toolbar ────────────────────────────────────────────────────────────── */
.group-mgmt :deep(.overview-header) {
  margin-bottom: 0;
  padding-inline: var(--jf-space-3);
}

.board-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1) var(--jf-space-2);
  padding: 0 var(--jf-space-3) var(--jf-space-2);
}

.board-search {
  flex: 0 1 320px;
}

.board-hint {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.group-mgmt > .state-view {
  margin: 0 var(--jf-space-3);
}

/* ─── Board ──────────────────────────────────────────────────────────────── */
.group-board {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 1rem;
  padding: 0 1.5rem 1.5rem;
  overflow-x: auto;
  overflow-y: hidden;
  flex: 1;
  /* Smooth scrolling on tablet touch */
  -webkit-overflow-scrolling: touch;
  scroll-snap-type: x proximity;
}

/* ─── Column ─────────────────────────────────────────────────────────────── */
.group-column {
  flex: 0 0 270px;
  display: flex;
  flex-direction: column;
  background: var(--p-content-hover-background);
  border: 1.5px solid var(--p-content-border-color);
  border-radius: 14px;
  max-height: calc(100vh - 200px);
  scroll-snap-align: start;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.group-column.drop-target {
  border-color: var(--p-primary-400);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-500) 25%, transparent);
  background: color-mix(in srgb, var(--p-primary-500) 10%, var(--p-content-background));
}

.unassigned-column {
  border-style: dashed;
  opacity: 0.85;
}

.unassigned-column.drop-target {
  opacity: 1;
}

/* ─── Column header ──────────────────────────────────────────────────────── */
.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 0.75rem 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
  flex-shrink: 0;
}

.column-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.column-name {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.column-icon {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.column-count {
  min-width: 1.75rem;
  padding: 0 var(--jf-space-1);
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--jf-color-text);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  line-height: 1.5rem;
  text-align: center;
}

.rename-field {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  min-width: 0;
}

.rename-input {
  width: 100%;
  min-height: var(--jf-touch-target);
}

.field-error {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-semibold);
  color: var(--p-red-700);
}

.app-dark .field-error {
  color: var(--p-red-300);
}

.column-actions {
  display: flex;
  gap: 0.1rem;
  flex-shrink: 0;
}

.column-actions :deep(.p-button) {
  width: var(--jf-touch-target);
  height: var(--jf-touch-target);
}

/* ─── Column body ────────────────────────────────────────────────────────── */
.column-body {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
}

/* ─── Card list transitions ──────────────────────────────────────────────── */
.card-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-height: 2rem;
}

.card-list-move,
.card-list-enter-active,
.card-list-leave-active {
  transition: all 0.2s ease;
}

.card-list-enter-from,
.card-list-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.card-list-leave-active {
  position: absolute;
  width: 100%;
}

/* ─── Empty state ────────────────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 1.5rem 1rem;
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
  text-align: center;
}

.empty-icon {
  font-size: 1.5rem;
  opacity: 0.4;
}

/* ─── Add-group tile ─────────────────────────────────────────────────────── */
.add-group-tile {
  font: inherit;
  background: transparent;
  flex: 0 0 200px;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: 2px dashed var(--p-content-border-color);
  border-radius: 14px;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  scroll-snap-align: start;
  align-self: flex-start;
  padding: 1rem;
}

.add-group-tile:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.add-group-tile:hover {
  border-color: var(--p-primary-400);
  color: var(--p-primary-400);
  background: color-mix(in srgb, var(--p-primary-500) 10%, var(--p-content-background));
}

.add-icon {
  font-size: 1.75rem;
}

/* ─── Dialog ─────────────────────────────────────────────────────────────── */
.dialog-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.25rem 0;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--p-text-color);
}

/* ─── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 767px) {
  .group-mgmt :deep(.overview-header) {
    flex-wrap: wrap;
    gap: var(--jf-space-1);
    padding: 0 var(--jf-space-2);
  }

  .board-toolbar {
    padding: 0 var(--jf-space-2) var(--jf-space-1-5);
  }

  .board-search {
    flex: 1 1 100%;
  }

  .group-mgmt > .state-view {
    margin: 0 var(--jf-space-2);
  }

  .group-board {
    flex-direction: column;
    overflow-x: hidden;
    overflow-y: auto;
    padding: 0 1rem 1rem;
  }

  .group-column {
    flex: none;
    width: 100%;
    max-height: none;
  }

  .add-group-tile {
    flex: none;
    width: 100%;
    min-height: 80px;
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .group-column {
    flex: 0 0 240px;
  }
}
</style>
