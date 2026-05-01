<template>
  <div class="lists-overview">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <i class="pi pi-list-check title-icon"></i>
          Listen
        </h1>
        <Tag :value="`${store.lists.length} Listen`" severity="secondary" />
      </div>
      <Button label="Neue Liste" icon="pi pi-plus" @click="openCreateDialog" />
    </div>

    <!-- Search -->
    <div v-if="store.lists.length > 0" class="search-bar">
      <span class="p-input-icon-left search-input-wrap">
        <i class="pi pi-search" />
        <InputText
          v-model="searchQuery"
          placeholder="Listen durchsuchen…"
          class="search-input"
        />
      </span>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">
      <ProgressSpinner style="width: 48px; height: 48px" />
      <span>Lade Listen…</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="store.lists.length === 0" class="empty-hero">
      <i class="pi pi-list-check empty-big-icon"></i>
      <h2>Noch keine Listen</h2>
      <p>Erstelle deine erste Liste, um Mitglieder zu organisieren.</p>
      <Button label="Erste Liste erstellen" icon="pi pi-plus" @click="openCreateDialog" />
    </div>

    <!-- No search results -->
    <div v-else-if="filteredLists.length === 0 && searchQuery" class="empty-hero">
      <i class="pi pi-search empty-big-icon"></i>
      <h2>Keine Listen gefunden</h2>
      <p>Kein Ergebnis für „{{ searchQuery }}"</p>
    </div>

    <!-- Cards grid -->
    <TransitionGroup v-else name="card-grid" tag="div" class="lists-grid">
      <Card
        v-for="list in filteredLists"
        :key="list.id"
        class="list-card"
        :style="{ '--list-color': list.color }"
        @click="openList(list.id)"
      >
        <template #header>
          <div class="card-color-bar" :style="{ background: list.color }"></div>
        </template>
        <template #content>
          <div class="card-content">
            <div class="card-top">
              <h3 class="list-name">{{ list.name }}</h3>
              <div class="card-actions">
                <Button
                  icon="pi pi-envelope"
                  text
                  rounded
                  size="small"
                  v-tooltip.top="'E-Mail an alle in dieser Liste'"
                  @click.stop="emailList(list)"
                />
                <Button
                  icon="pi pi-pencil"
                  text
                  rounded
                  size="small"
                  v-tooltip.top="'Bearbeiten'"
                  @click.stop="openEditDialog(list)"
                />
                <Button
                  icon="pi pi-trash"
                  text
                  rounded
                  size="small"
                  severity="danger"
                  v-tooltip.top="'Löschen'"
                  @click.stop="confirmDelete(list)"
                />
              </div>
            </div>

            <p v-if="list.description" class="list-description">{{ list.description }}</p>

            <!-- Progress bar -->
            <div class="progress-row">
              <div class="progress-bar-wrap">
                <div
                  class="progress-bar-fill"
                  :style="{
                    width: list.member_count ? `${(list.checked_count / list.member_count) * 100}%` : '0%',
                    background: list.color,
                  }"
                ></div>
              </div>
              <span class="progress-label">{{ list.checked_count }} / {{ list.member_count }}</span>
            </div>

            <div class="meta-row">
              <Tag
                :value="`${list.member_count} Mitglieder`"
                severity="secondary"
                rounded
                class="member-tag"
              />
              <span class="updated-at">{{ formatDate(list.updated_at) }}</span>
            </div>
          </div>
        </template>
      </Card>
    </TransitionGroup>

    <!-- Create / Edit Dialog -->
    <Dialog
      v-model:visible="showFormDialog"
      :header="editingList ? 'Liste bearbeiten' : 'Neue Liste erstellen'"
      modal
      :style="{ width: 'min(480px, 95vw)' }"
    >
      <div class="dialog-form">
        <div class="form-field">
          <label class="field-label">Name *</label>
          <InputText
            v-model="formData.name"
            placeholder="z.B. Ausflug 2025"
            class="w-full"
            autofocus
            @keyup.enter="saveForm"
          />
        </div>
        <div class="form-field">
          <label class="field-label">Beschreibung</label>
          <Textarea
            v-model="formData.description"
            rows="2"
            placeholder="Optional: kurze Beschreibung"
            class="w-full"
          />
        </div>
        <div class="form-field">
          <label class="field-label">Farbe</label>
          <div class="color-row">
            <div
              v-for="c in colorPresets"
              :key="c"
              class="color-swatch"
              :class="{ 'color-swatch--active': formData.color === c }"
              :style="{ background: c }"
              @click="formData.color = c"
            ></div>
            <input type="color" v-model="formData.color" class="color-picker" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Abbrechen" text @click="showFormDialog = false" />
        <Button
          :label="editingList ? 'Speichern' : 'Erstellen'"
          icon="pi pi-check"
          :disabled="!formData.name.trim()"
          :loading="store.saving"
          @click="saveForm"
        />
      </template>
    </Dialog>

    <ConfirmDialog />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Toast from 'primevue/toast'
import { useMemberListsStore } from '@/stores/lists'
import { useMembersStore } from '@/stores/members'
import type { MemberList } from '@/types/lists'

const router = useRouter()
const store = useMemberListsStore()
const membersStore = useMembersStore()
const confirm = useConfirm()
const toast = useToast()

const colorPresets = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
  '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16',
]

// ── Search ────────────────────────────────────────────────────────────────
const searchQuery = ref('')
const filteredLists = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return store.lists
  return store.lists.filter(
    (l) =>
      l.name.toLowerCase().includes(q) ||
      (l.description ?? '').toLowerCase().includes(q),
  )
})

// ── Navigation ────────────────────────────────────────────────────────────
function openList(id: number) {
  router.push({ name: 'list-detail', params: { id } })
}

// ── Email integration ─────────────────────────────────────────────────────
async function emailList(list: MemberList) {
  // We need member IDs — fetch the full list if not already loaded
  let detail = store.currentList?.id === list.id ? store.currentList : null
  if (!detail) {
    await store.fetchList(list.id)
    detail = store.currentList
  }
  if (!detail) return
  const memberIds = detail.entries.map((e) => e.member.id)
  router.push({
    name: 'emails-compose',
    state: { preselectedMemberIds: memberIds, preselectSource: list.name },
  })
}

// ── Create / Edit ─────────────────────────────────────────────────────────
const showFormDialog = ref(false)
const editingList = ref<MemberList | null>(null)
const formData = reactive({ name: '', description: '', color: '#3B82F6' })

function openCreateDialog() {
  editingList.value = null
  formData.name = ''
  formData.description = ''
  formData.color = '#3B82F6'
  showFormDialog.value = true
}

function openEditDialog(list: MemberList) {
  editingList.value = list
  formData.name = list.name
  formData.description = list.description
  formData.color = list.color
  showFormDialog.value = true
}

async function saveForm() {
  if (!formData.name.trim()) return
  try {
    if (editingList.value) {
      await store.updateList(editingList.value.id, { ...formData })
      toast.add({ severity: 'success', summary: 'Gespeichert', detail: formData.name, life: 2500 })
    } else {
      const created = await store.createList({ ...formData })
      toast.add({ severity: 'success', summary: 'Erstellt', detail: created.name, life: 2500 })
    }
    showFormDialog.value = false
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht gespeichert werden.', life: 4000 })
  }
}

// ── Delete ────────────────────────────────────────────────────────────────
function confirmDelete(list: MemberList) {
  confirm.require({
    header: 'Liste löschen',
    message: `Liste „${list.name}" mit ${list.member_count} Mitglieder(n) wirklich löschen?`,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    acceptClass: 'p-button-danger',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      await store.deleteList(list.id)
      toast.add({ severity: 'success', summary: 'Gelöscht', detail: `„${list.name}" entfernt.`, life: 2500 })
    },
  })
}

// ── Format ────────────────────────────────────────────────────────────────
function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(() => {
  store.fetchLists()
  membersStore.fetchMembers({ limit: 1000 })
})
</script>

<style scoped>
.lists-overview {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding-bottom: 2rem;
}

/* ─── Header ─────────────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.5rem 1rem;
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

/* ─── Search ─────────────────────────────────────────────────────────────── */
.search-bar {
  padding: 0 1.5rem 0.75rem;
}

.search-input-wrap {
  display: block;
  max-width: 360px;
}

.search-input {
  width: 100%;
}

/* ─── Loading / Empty ────────────────────────────────────────────────────── */
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

.empty-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 4rem 2rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.empty-big-icon {
  font-size: 4rem;
  opacity: 0.25;
}

.empty-hero h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--p-text-color);
}

.empty-hero p {
  margin: 0;
  font-size: 0.9rem;
}

/* ─── Grid ───────────────────────────────────────────────────────────────── */
.lists-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  padding: 0 1.5rem;
}

/* ─── Card ───────────────────────────────────────────────────────────────── */
.list-card {
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.15s;
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
}

.list-card:hover {
  box-shadow: 0 4px 20px color-mix(in srgb, var(--p-surface-950) 10%, transparent);
  transform: translateY(-2px);
}

.card-color-bar {
  height: 5px;
  width: 100%;
}

:deep(.p-card-header) {
  padding: 0 !important;
}

:deep(.p-card-body) {
  padding: 0 !important;
}

:deep(.p-card-content) {
  padding: 0 !important;
}

.card-content {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.list-name {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
  flex: 1;
  min-width: 0;
}

.card-actions {
  display: flex;
  gap: 0;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.list-card:hover .card-actions {
  opacity: 1;
}

@media (hover: none) {
  .card-actions {
    opacity: 1;
  }
}

.list-description {
  margin: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ─── Progress bar ───────────────────────────────────────────────────────── */
.progress-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-bar-wrap {
  flex: 1;
  height: 6px;
  background: var(--p-content-border-color);
  border-radius: 99px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.4s ease;
  min-width: 0;
}

.progress-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-text-color);
  white-space: nowrap;
  flex-shrink: 0;
}

/* ─── Meta row ───────────────────────────────────────────────────────────── */
.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.member-tag {
  font-size: 0.7rem !important;
}

.updated-at {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}

/* ─── Form dialog ────────────────────────────────────────────────────────── */
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

/* ─── Transitions ────────────────────────────────────────────────────────── */
.card-grid-enter-active,
.card-grid-leave-active {
  transition: all 0.25s ease;
}

.card-grid-enter-from,
.card-grid-leave-to {
  opacity: 0;
  transform: scale(0.92);
}

/* ─── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 600px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .lists-grid {
    grid-template-columns: 1fr;
    padding: 0 1rem;
  }
}
</style>
