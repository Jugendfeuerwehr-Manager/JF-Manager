<template>
  <div class="group-mgmt">
    <!-- Page header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <i class="pi pi-sitemap title-icon"></i>
          Gruppenmanagement
        </h1>
        <Tag
          :value="`${totalMemberCount} Mitglieder`"
          severity="secondary"
          class="total-tag"
        />
      </div>

      <div class="header-right">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Mitglieder suchen…"
            class="search-input"
          />
        </IconField>
        <Button
          label="Neue Gruppe"
          icon="pi pi-plus"
          @click="openCreateDialog"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">
      <ProgressSpinner style="width: 48px; height: 48px" />
      <span>Lade Daten…</span>
    </div>

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
            <span class="column-name">
              <i class="pi pi-user-minus column-icon"></i>
              Ohne Gruppe
            </span>
            <Tag
              :value="String(filteredUnassigned.length)"
              severity="secondary"
              rounded
            />
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
              <span class="column-name">
                <i class="pi pi-tag column-icon"></i>
                {{ group.name }}
              </span>
              <Tag
                :value="String(filteredGroupMembers(group.id).length)"
                rounded
              />
            </template>

            <!-- Rename mode -->
            <InputText
              v-else
              v-model="renamingName"
              class="rename-input"
              @keyup.enter="saveRename(group)"
              @keyup.escape="cancelRename"
              @blur="saveRename(group)"
            />
          </div>

          <!-- Actions: view mode -->
          <div v-if="renamingId !== group.id" class="column-actions">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              size="small"
              v-tooltip.top="'Umbenennen'"
              @click="startRename(group)"
            />
            <Button
              icon="pi pi-trash"
              text
              rounded
              size="small"
              severity="danger"
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
              size="small"
              severity="success"
              v-tooltip.top="'Speichern'"
              :loading="store.saving"
              @click="saveRename(group)"
            />
            <Button
              icon="pi pi-times"
              text
              rounded
              size="small"
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
      <div class="add-group-tile" @click="openCreateDialog">
        <i class="pi pi-plus-circle add-icon"></i>
        <span>Neue Gruppe</span>
      </div>
    </div>

    <!-- Create group dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      header="Neue Gruppe erstellen"
      modal
      :style="{ width: 'min(420px, 92vw)' }"
    >
      <div class="dialog-field">
        <label for="new-group-name" class="field-label">Gruppenname</label>
        <InputText
          id="new-group-name"
          v-model="newGroupName"
          placeholder="z.B. Gruppe Alpha"
          class="w-full"
          autofocus
          @keyup.enter="createGroup"
        />
      </div>
      <template #footer>
        <Button label="Abbrechen" text @click="showCreateDialog = false" />
        <Button
          label="Erstellen"
          icon="pi pi-check"
          :disabled="!newGroupName.trim()"
          :loading="store.saving"
          @click="createGroup"
        />
      </template>
    </Dialog>

    <ConfirmDialog />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import Toast from 'primevue/toast'
import MemberGroupCard from '@/components/members/atoms/MemberGroupCard.vue'
import { useGroupsStore } from '@/stores/groups'
import type { Group, Member } from '@/types/members'

// ─── Constants ────────────────────────────────────────────────────────────────
const UNASSIGNED_KEY = '__unassigned__'

// ─── Store / services ─────────────────────────────────────────────────────────
const store = useGroupsStore()
const confirm = useConfirm()
const toast = useToast()

// ─── Search ───────────────────────────────────────────────────────────────────
const searchQuery = ref('')

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

const filteredUnassigned = computed(() =>
  store.members.filter((m) => !m.group && matchesSearch(m)),
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
      summary: 'Fehler',
      detail: 'Zuweisung konnte nicht gespeichert werden.',
      life: 4000,
    })
  }
}

// ─── Create group ─────────────────────────────────────────────────────────────
const showCreateDialog = ref(false)
const newGroupName = ref('')

function openCreateDialog() {
  newGroupName.value = ''
  showCreateDialog.value = true
}

async function createGroup() {
  if (!newGroupName.value.trim()) return
  try {
    await store.createGroup(newGroupName.value.trim())
    showCreateDialog.value = false
    toast.add({ severity: 'success', summary: 'Erstellt', detail: newGroupName.value.trim(), life: 2500 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Gruppe konnte nicht erstellt werden.', life: 4000 })
  }
}

// ─── Rename group ─────────────────────────────────────────────────────────────
const renamingId = ref<number | null>(null)
const renamingName = ref('')

function startRename(group: Group) {
  renamingId.value = group.id
  renamingName.value = group.name
}

function cancelRename() {
  renamingId.value = null
}

async function saveRename(group: Group) {
  if (renamingId.value !== group.id) return
  const trimmed = renamingName.value.trim()
  if (!trimmed || trimmed === group.name) {
    cancelRename()
    return
  }
  try {
    await store.updateGroup(group.id, trimmed)
    cancelRename()
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Name konnte nicht gespeichert werden.', life: 4000 })
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
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Gruppe konnte nicht gelöscht werden.', life: 4000 })
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([store.fetchGroups(), store.fetchAllMembers()])
})
</script>

<style scoped>
/* ─── Layout ──────────────────────────────────────────────────────────────── */
.group-mgmt {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ─── Header ─────────────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.5rem 1rem;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.page-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color);
}

.title-icon {
  color: var(--p-primary-500);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.search-input {
  width: 220px;
}

/* ─── Loading ────────────────────────────────────────────────────────────── */
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

.rename-input {
  flex: 1;
  font-size: 0.875rem;
  height: 1.85rem;
  padding: 0.2rem 0.5rem;
}

.column-actions {
  display: flex;
  gap: 0.1rem;
  flex-shrink: 0;
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
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    padding: 1rem;
  }

  .header-right {
    width: 100%;
  }

  .search-input {
    width: 100%;
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
