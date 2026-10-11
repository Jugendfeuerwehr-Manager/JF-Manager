<template>
  <div class="list-detail">
    <StateView v-if="store.loading && !store.currentList" kind="loading" title="Liste wird geladen …" />

    <template v-else-if="store.currentList">
      <header class="list-head">
        <div class="list-head__top">
          <router-link :to="{ name: 'lists' }" class="back-link"><i class="pi pi-arrow-left" aria-hidden="true"></i>Listen</router-link>
          <SaveStateIndicator :state="saveState" />
        </div>
        <div class="list-head__main">
          <div class="list-head__title">
            <h1><span class="color-dot" :style="{ background: store.currentList.color }" aria-hidden="true"></span>{{ store.currentList.name }}</h1>
            <p v-if="store.currentList.description" class="list-head__description">{{ store.currentList.description }}</p>
            <p class="list-head__meta">{{ totalCount }} {{ totalCount === 1 ? 'Person' : 'Personen' }}</p>
          </div>
          <div class="list-head__actions">
            <Button
              :label="editing ? 'Fertig' : 'Einträge verwalten'"
              :icon="editing ? 'pi pi-check' : 'pi pi-user-edit'"
              :severity="editing ? undefined : 'secondary'"
              :outlined="!editing"
              :aria-pressed="editing"
              @click="editing = !editing"
            />
            <Button
              icon="pi pi-ellipsis-v"
              severity="secondary"
              text
              aria-label="Weitere Aktionen"
              aria-haspopup="true"
              aria-controls="list_actions_menu"
              @click="(event: MouseEvent) => actionsMenu.toggle(event)"
            />
            <Menu id="list_actions_menu" ref="actionsMenu" :model="actionItems" :popup="true" />
          </div>
        </div>

        <div class="progress">
          <div class="progress__labels">
            <span><strong>{{ checkedCount }}</strong> von {{ totalCount }} erledigt</span>
            <span class="muted">{{ openCount }} offen</span>
          </div>
          <div
            class="progress__track"
            role="progressbar"
            aria-label="Erledigt"
            aria-valuemin="0"
            :aria-valuemax="totalCount"
            :aria-valuenow="checkedCount"
            :aria-valuetext="`${checkedCount} von ${totalCount} erledigt`"
          >
            <div class="progress__bar" :style="{ width: `${progressPercent}%` }"></div>
          </div>
        </div>
      </header>

      <section v-if="editing" class="add-panel" aria-labelledby="add-panel-title">
        <h2 id="add-panel-title"><i class="pi pi-user-plus" aria-hidden="true"></i>Mitglieder hinzufügen</h2>
        <div class="add-controls">
          <AutoComplete
            v-model="memberSearchText"
            :suggestions="memberSuggestions"
            placeholder="Mitglied suchen …"
            option-label="full_name"
            class="add-autocomplete"
            input-id="add-member"
            aria-label="Mitglied zum Hinzufügen suchen"
            :pt="{ pcInputText: { root: { class: 'w-full' } } }"
            @complete="searchMembers"
            @option-select="onMemberSelect"
            @keydown.enter="onAutoCompleteEnter"
          />
          <Button label="Alle hinzufügen" icon="pi pi-users" severity="secondary" outlined @click="addAllMembers" />
        </div>
        <div v-if="availableGroups.length" class="group-chips">
          <span class="muted">Gruppe hinzufügen:</span>
          <button v-for="group in availableGroups" :key="group.id" type="button" class="chip" @click="addGroup(group.id)">
            <i class="pi pi-plus" aria-hidden="true"></i>{{ group.name }}
          </button>
        </div>
      </section>

      <section class="checklist" aria-label="Einträge">
        <div class="checklist__controls">
          <div class="segmented" role="group" aria-label="Filter">
            <button type="button" :aria-pressed="filterMode === 'unchecked'" @click="filterMode = 'unchecked'">Offen ({{ openCount }})</button>
            <button type="button" :aria-pressed="filterMode === 'checked'" @click="filterMode = 'checked'">Erledigt ({{ checkedCount }})</button>
            <button type="button" :aria-pressed="filterMode === 'all'" @click="filterMode = 'all'">Alle</button>
          </div>
          <IconField class="checklist__search">
            <InputIcon class="pi pi-search" />
            <InputText v-model="listSearch" placeholder="Name suchen" aria-label="Einträge durchsuchen" class="w-full" />
          </IconField>
        </div>

        <StateView
          v-if="filteredEntries.length === 0"
          kind="empty"
          :title="emptyTitle"
          :message="store.currentList.entries.length === 0 ? 'Über „Einträge verwalten“ fügst du Mitglieder hinzu.' : ''"
        />

        <ul v-else class="entry-list">
          <li v-for="entry in filteredEntries" :key="entry.member.id" class="entry" :class="{ 'entry--checked': entry.checked }">
            <button
              type="button"
              role="checkbox"
              class="entry__toggle"
              :aria-checked="entry.checked"
              :disabled="pending.has(entry.member.id)"
              @click="toggle(entry)"
            >
              <span class="entry__box" aria-hidden="true"><i v-if="entry.checked" class="pi pi-check"></i></span>
              <span class="entry__text">
                <span class="entry__name">{{ entry.member.full_name }}</span>
                <span class="entry__meta">{{ entryMeta(entry) }}</span>
                <span v-if="entry.notes && !editing" class="entry__note"><i class="pi pi-comment" aria-hidden="true"></i>{{ entry.notes }}</span>
              </span>
            </button>
            <div v-if="editing" class="entry__edit">
              <InputText
                v-model="localNotes[entry.member.id]"
                placeholder="Notiz"
                :aria-label="`Notiz zu ${entry.member.full_name}`"
                class="entry__notes"
                @blur="saveNotes(entry.member.id)"
                @keydown.enter="saveNotes(entry.member.id)"
              />
              <Button
                icon="pi pi-times"
                text
                severity="danger"
                :aria-label="`${entry.member.full_name} aus der Liste entfernen`"
                @click="removeMember(entry.member.id)"
              />
            </div>
          </li>
        </ul>

        <Button
          v-if="openCount > 0 && !editing"
          label="Offene erinnern …"
          icon="pi pi-envelope"
          severity="secondary"
          outlined
          class="remind-button"
          @click="handleEmail('open')"
        />
      </section>

      <AttachmentsSection
        :source-id="store.currentList.id"
        source-type="memberList"
        title="Anhänge"
        :allow-manage="true"
      />
    </template>

    <StateView v-else-if="loadErrorKind" :kind="loadErrorKind" title="Liste konnte nicht geladen werden" @retry="loadList" />

    <!-- Edit dialog -->
    <Dialog
      v-model:visible="showEditDialog"
      header="Liste bearbeiten"
      modal
      :style="{ width: 'min(480px, 95vw)' }"
    >
      <div class="dialog-form">
        <div class="form-field">
          <label for="list-name" class="field-label">Name</label>
          <InputText id="list-name" v-model="editForm.name" class="w-full" autofocus @keyup.enter="saveEdit" />
        </div>
        <div class="form-field">
          <label for="list-description" class="field-label">Beschreibung</label>
          <Textarea id="list-description" v-model="editForm.description" rows="2" class="w-full" />
        </div>
        <div class="form-field">
          <span class="field-label">Farbe</span>
          <div class="color-row">
            <button
              v-for="c in colorPresets"
              :key="c"
              type="button"
              class="color-swatch"
              :class="{ 'color-swatch--active': editForm.color === c }"
              :style="{ background: c }"
              :aria-label="`Farbe ${c}`"
              :aria-pressed="editForm.color === c"
              @click="editForm.color = c"
            ></button>
            <input v-model="editForm.color" type="color" class="color-picker" aria-label="Eigene Farbe" />
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

    <BulkPreviewDialog
      :visible="bulk !== null"
      :title="bulk?.title ?? ''"
      :intro="bulk?.intro ?? ''"
      :note="bulk?.note"
      :names="bulk?.names ?? []"
      :confirm-label="bulk?.confirmLabel ?? ''"
      :danger="bulk?.danger"
      :busy="bulkBusy"
      @cancel="bulk = null"
      @confirm="confirmBulk"
    />

    <MemberExportDialog
      v-model="showExportDialog"
      :exporting="store.loading"
      :extra-column-groups="listExtraColumnGroups"
      :extra-default-columns="['list_checked', 'list_notes']"
      @export="handleExportExcel"
    />
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { canExport } from '@/utils/exportPermission'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Menu from 'primevue/menu'
import Textarea from 'primevue/textarea'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import SaveStateIndicator, { type SaveState } from '@/components/common/SaveStateIndicator.vue'
import BulkPreviewDialog from '@/components/lists/molecules/BulkPreviewDialog.vue'
import { getApiErrorMessage } from '@/utils/apiError'
import { classifyApiError } from '@/utils/apiError'
import AttachmentsSection from '@/components/qualifications/organisms/AttachmentsSection.vue'
import MemberExportDialog from '@/components/members/molecules/MemberExportDialog.vue'
import { ListEntryConflictError, useMemberListsStore } from '@/stores/lists'
import { useMembersStore } from '@/stores/members'
import { useGroupsStore } from '@/stores/groups'
import { useListPdf } from '@/composables/useListPdf'
import type { MemberListEntry } from '@/types/lists'
import type { Member } from '@/types/members'

const exportAuth = useAuthStore()
// ── Route & stores ────────────────────────────────────────────────────────
const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const store = useMemberListsStore()
const membersStore = useMembersStore()
const groupsStore = useGroupsStore()
const { generateChecklist } = useListPdf()

// ── Export dialog ─────────────────────────────────────────────────────────
const showExportDialog = ref(false)

const listExtraColumnGroups = [
  {
    label: 'Listen-Daten',
    columns: [
      { key: 'list_checked', label: 'Anwesend' },
      { key: 'list_checked_at', label: 'Anwesend seit' },
      { key: 'list_notes', label: 'Notiz (Liste)' },
    ],
  },
]

async function handleExportExcel(columns: string[]) {
  const listId = store.currentList?.id
  if (!listId) return
  try {
    await store.exportExcel(listId, columns)
    showExportDialog.value = false
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Export fehlgeschlagen.', life: 4000 })
  }
}

const listId = computed(() => Number(route.params.id))

// ── Derived counts ────────────────────────────────────────────────────────
const checkedCount = computed(() => store.currentList?.entries.filter((e) => e.checked).length ?? 0)
const totalCount = computed(() => store.currentList?.entries.length ?? 0)
const openCount = computed(() => totalCount.value - checkedCount.value)
const progressPercent = computed(() => (totalCount.value ? Math.round((checkedCount.value / totalCount.value) * 100) : 0))

// ── Modes and save state ──────────────────────────────────────────────────
/** Checking off is the default; adding, notes and removal live in a separate mode. */
const editing = ref(false)
const pending = reactive(new Set<number>())
const failedSaves = ref(0)
/** Set when the server refused a stale write and its current state is shown instead. */
const conflictShown = ref(false)
const saveState = computed<SaveState>(() => {
  if (pending.size) return 'saving'
  if (failedSaves.value) return 'error'
  if (conflictShown.value) return 'conflict'
  return 'saved'
})

function reportConflict(error: ListEntryConflictError, what: 'check' | 'notes') {
  conflictShown.value = true
  failedSaves.value = 0
  const name = error.memberName || 'Der Eintrag'
  const detail = what === 'notes'
    ? `Die Notiz zu ${name} wurde inzwischen von jemand anderem geändert. Der aktuelle Stand wird angezeigt; deine Notiz wurde nicht gespeichert.`
    : `${name} wurde inzwischen von jemand anderem ${error.current.checked ? 'abgehakt' : 'wieder auf offen gesetzt'}. Der aktuelle Stand wird angezeigt.`
  toast.add({ severity: 'warn', summary: 'Inzwischen geändert', detail, life: 7000 })
}

async function toggle(entry: MemberListEntry) {
  const memberId = entry.member.id
  if (!store.currentList || pending.has(memberId)) return
  pending.add(memberId)
  try {
    // An explicit target state plus the seen version: a stale tap never flips someone else's change.
    await store.setCheck(store.currentList.id, memberId, !entry.checked)
    failedSaves.value = 0
    conflictShown.value = false
  } catch (error) {
    if (error instanceof ListEntryConflictError) {
      reportConflict(error, 'check')
    } else {
      failedSaves.value += 1
      toast.add({ severity: 'error', summary: 'Nicht gespeichert', detail: 'Der Haken wurde zurückgenommen. Bitte erneut versuchen.', life: 5000 })
    }
  } finally {
    pending.delete(memberId)
  }
}

function formatCheckedAt(value: string) {
  const date = new Date(value)
  const time = date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  if (date.toDateString() === new Date().toDateString()) return `heute ${time}`
  return `${date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })}, ${time}`
}

function entryMeta(entry: MemberListEntry) {
  if (entry.checked) return entry.checked_at ? `erledigt ${formatCheckedAt(entry.checked_at)}` : 'erledigt'
  return [entry.member.group?.name, 'offen'].filter(Boolean).join(' · ')
}

const emptyTitle = computed(() => {
  if (!store.currentList?.entries.length) return 'Noch keine Mitglieder in dieser Liste'
  if (filterMode.value === 'unchecked' && !listSearch.value) return 'Alles erledigt'
  return 'Keine Einträge für diesen Filter'
})

// ── Actions menu ──────────────────────────────────────────────────────────
const actionsMenu = ref()
const actionItems = computed(() => {
  const list = store.currentList
  const items = [
    { label: 'Alle abhaken …', icon: 'pi pi-check-square', command: () => previewBulkCheck(true) },
    { label: 'Alle Haken entfernen …', icon: 'pi pi-stop', command: () => previewBulkCheck(false) },
    { separator: true },
    { label: 'E-Mail an alle', icon: 'pi pi-envelope', command: () => handleEmail('all') },
    { label: 'PDF erstellen', icon: 'pi pi-file-pdf', command: () => handlePdf() },
  ]
  if (list && canExport(exportAuth.user, 'export_memberlist', list.department)) {
    items.push({ label: 'Excel exportieren', icon: 'pi pi-file-excel', command: () => { showExportDialog.value = true } })
  }
  items.push({ separator: true }, { label: 'Name und Farbe bearbeiten', icon: 'pi pi-pencil', command: () => openEditDialog() })
  return items
})

// ── Groups for quick bulk-add ─────────────────────────────────────────────
const availableGroups = computed(() => groupsStore.groups)

// ── Checklist filter / search ─────────────────────────────────────────────
const listSearch = ref('')
const filterMode = ref<'all' | 'checked' | 'unchecked'>('all')

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

function addAllMembers() {
  const alreadyIds = new Set(store.currentList?.entries.map((e) => e.member.id) ?? [])
  const toAdd = membersStore.members.filter((m) => !alreadyIds.has(m.id)).map((m) => m.id)
  void previewAdd(toAdd, 'Alle Mitglieder hinzufügen', 'Alle bereits in der Liste')
}

function addGroup(groupId: number) {
  const alreadyIds = new Set(store.currentList?.entries.map((e) => e.member.id) ?? [])
  const toAdd = membersStore.members
    .filter((m) => !alreadyIds.has(m.id) && m.group?.id === groupId)
    .map((m) => m.id)
  const group = groupsStore.groups.find((g) => g.id === groupId)
  void previewAdd(toAdd, `Gruppe „${group?.name ?? ''}“ hinzufügen`, 'Alle Mitglieder der Gruppe sind bereits in der Liste')
}

// ── Remove member ─────────────────────────────────────────────────────────
/** Removing drops the check state and note of that person, so it is confirmed first. */
function removeMember(memberId: number) {
  const entry = store.currentList?.entries.find((e) => e.member.id === memberId)
  confirm.require({
    header: 'Aus der Liste entfernen?',
    message: `${entry?.member.full_name ?? 'Der Eintrag'} wird aus der Liste entfernt; Haken und Notiz gehen dabei verloren.`,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Entfernen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await store.removeMember(listId.value, memberId)
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht entfernt werden.', life: 3000 })
      }
    },
  })
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
  const entry = store.currentList?.entries.find((e) => e.member.id === memberId)
  const notes = localNotes[memberId] ?? ''
  if (entry && entry.notes === notes) return
  try {
    await store.updateEntryNotes(listId.value, memberId, notes)
    conflictShown.value = false
  } catch (error) {
    if (error instanceof ListEntryConflictError) {
      localNotes[memberId] = error.current.notes
      reportConflict(error, 'notes')
    } else {
      failedSaves.value += 1
      toast.add({ severity: 'error', summary: 'Notiz nicht gespeichert', detail: getApiErrorMessage(error, 'Bitte erneut versuchen.'), life: 5000 })
    }
  }
}

// ── Bulk actions: always preview, then confirm (UX-03.1) ─────────────────
interface BulkPlan {
  kind: 'check' | 'uncheck' | 'add'
  title: string
  intro: string
  note?: string
  names: string[]
  memberIds: number[]
  confirmLabel: string
  danger?: boolean
}
const bulk = ref<BulkPlan | null>(null)
const bulkBusy = ref(false)

async function previewBulkCheck(checked: boolean) {
  if (!store.currentList) return
  try {
    const preview = await store.previewBulkCheck(store.currentList.id, checked)
    if (!preview.count) {
      toast.add({ severity: 'info', summary: checked ? 'Alle sind bereits abgehakt' : 'Keine Haken gesetzt', life: 2500 })
      return
    }
    bulk.value = {
      kind: checked ? 'check' : 'uncheck',
      title: checked ? 'Alle abhaken?' : 'Alle Haken entfernen?',
      intro: checked
        ? `${preview.count} offene ${preview.count === 1 ? 'Eintrag wird' : 'Einträge werden'} als erledigt markiert:`
        : `${preview.count} erledigte ${preview.count === 1 ? 'Eintrag wird' : 'Einträge werden'} wieder auf offen gesetzt:`,
      note: checked ? undefined : 'Die Erledigt-Zeitpunkte gehen dabei verloren.',
      names: preview.entries.map((entry) => entry.name),
      memberIds: preview.entries.map((entry) => entry.member_id),
      confirmLabel: checked ? `${preview.count} abhaken` : `${preview.count} Haken entfernen`,
      danger: !checked,
    }
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Vorschau nicht möglich', detail: getApiErrorMessage(error, 'Bitte erneut versuchen.'), life: 5000 })
  }
}

async function previewAdd(memberIds: number[], title: string, emptyMessage: string) {
  if (!memberIds.length) {
    toast.add({ severity: 'info', summary: emptyMessage, life: 2500 })
    return
  }
  try {
    const preview = await store.previewBulkAdd(listId.value, memberIds)
    if (!preview.added) {
      toast.add({ severity: 'info', summary: emptyMessage, life: 2500 })
      return
    }
    bulk.value = {
      kind: 'add',
      title,
      intro: `${preview.added} ${preview.added === 1 ? 'Mitglied wird' : 'Mitglieder werden'} zur Liste hinzugefügt:`,
      note: preview.already_in_list ? `${preview.already_in_list} bereits in der Liste.` : undefined,
      names: preview.members.map((member) => member.name),
      memberIds: preview.members.map((member) => member.member_id),
      confirmLabel: `${preview.added} hinzufügen`,
    }
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Vorschau nicht möglich', detail: getApiErrorMessage(error, 'Bitte erneut versuchen.'), life: 5000 })
  }
}

async function confirmBulk() {
  const plan = bulk.value
  if (!plan || bulkBusy.value) return
  bulkBusy.value = true
  try {
    if (plan.kind === 'add') {
      const result = await store.bulkAdd(listId.value, plan.memberIds)
      toast.add({ severity: 'success', summary: `${result.added} ${result.added === 1 ? 'Mitglied' : 'Mitglieder'} hinzugefügt`, life: 2500 })
    } else {
      const result = await store.applyBulkCheck(listId.value, plan.kind === 'check', plan.memberIds)
      toast.add({
        severity: result.skipped ? 'warn' : 'success',
        summary: `${result.changed} ${result.changed === 1 ? 'Eintrag' : 'Einträge'} geändert`,
        detail: result.skipped ? `${result.skipped} hatte inzwischen schon jemand anderes geändert; der aktuelle Stand wird angezeigt.` : undefined,
        life: result.skipped ? 7000 : 2500,
      })
    }
    failedSaves.value = 0
    bulk.value = null
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Nicht gespeichert', detail: getApiErrorMessage(error, 'Die Änderung konnte nicht gespeichert werden.'), life: 5000 })
    await store.fetchList(listId.value).catch(() => undefined)
    bulk.value = null
  } finally {
    bulkBusy.value = false
  }
}

// ── PDF ───────────────────────────────────────────────────────────────────
const pdfLoading = ref(false)

async function handlePdf() {
  pdfLoading.value = true
  try {
    await store.fetchList(listId.value)
    if (!store.currentList) return
    await generateChecklist(store.currentList)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'PDF-Export fehlgeschlagen.', life: 4000 })
  } finally {
    pdfLoading.value = false
  }
}

// ── Email ─────────────────────────────────────────────────────────────────
function handleEmail(scope: 'all' | 'open') {
  if (!store.currentList) return
  const memberIds = store.currentList.entries.filter((e) => scope === 'all' || !e.checked).map((e) => e.member.id)
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

// ── Init ──────────────────────────────────────────────────────────────────
const loadErrorKind = ref<'error' | 'forbidden' | 'offline' | null>(null)

async function loadList() {
  loadErrorKind.value = null
  try {
    await store.fetchList(listId.value)
  } catch (error) {
    loadErrorKind.value = stateForError(classifyApiError(error))
  }
}

onMounted(async () => {
  await Promise.all([
    loadList(),
    membersStore.fetchMembers({ limit: 1000, ordering: 'lastname,name' }),
    groupsStore.fetchGroups(),
  ])
})
</script>

<style scoped>
.list-detail {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 960px;
  margin: 0 auto;
}

.list-head {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}

.list-head__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  color: var(--jf-color-primary);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.list-head__main {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--jf-space-1-5);
}

.list-head__title {
  flex: 1 1 280px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.list-head h1 {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  margin: 0;
  font-size: var(--jf-text-2xl);
  line-height: var(--jf-leading-tight);
  letter-spacing: -0.015em;
}

.color-dot {
  flex: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.list-head__description,
.list-head__meta,
.muted {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.list-head__actions {
  display: flex;
  gap: var(--jf-space-1);
}

.progress {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
}

.progress__labels {
  display: flex;
  justify-content: space-between;
  gap: var(--jf-space-1);
  font-size: var(--jf-text-sm);
}

.progress__track {
  height: 8px;
  border-radius: 999px;
  background: var(--jf-color-border);
  overflow: hidden;
}

.progress__bar {
  height: 100%;
  border-radius: 999px;
  background: var(--p-green-700);
  transition: width var(--jf-duration);
}

.app-dark .progress__bar {
  background: var(--p-green-400);
}

.add-panel {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-2);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
}

.add-panel h2 {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  margin: 0;
  font-size: var(--jf-text-md);
  font-weight: var(--jf-weight-semibold);
}

.add-controls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
}

.add-autocomplete {
  flex: 1 1 240px;
}

.group-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--p-surface-300);
  border-radius: 999px;
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
}

.checklist {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}

.checklist__controls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
}

.segmented {
  flex: 1 1 320px;
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-border);
}

.segmented button {
  flex: 1;
  min-height: 40px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--jf-color-text-muted);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
}

.segmented button[aria-pressed="true"] {
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  box-shadow: 0 1px 2px rgba(23, 32, 51, 0.12);
}

.checklist__search {
  flex: 1 1 200px;
}

.entry-list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  overflow: hidden;
}

.entry {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.entry + .entry {
  border-top: 1px solid var(--jf-color-border);
}

.entry__toggle {
  flex: 1 1 240px;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  min-height: 64px;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 0;
  background: transparent;
  color: var(--jf-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.entry__toggle:hover {
  background: var(--surface-hover);
}

.entry__toggle:disabled {
  cursor: progress;
}

.entry__box {
  flex: none;
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 2px solid var(--p-surface-400);
  border-radius: 8px;
  color: #fff;
  font-size: 0.875rem;
}

.entry--checked .entry__box {
  border-color: var(--p-green-700);
  background: var(--p-green-700);
}

.entry__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.entry__name {
  font-weight: var(--jf-weight-semibold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry__meta {
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.entry--checked .entry__meta {
  color: var(--p-green-800);
}

.app-dark .entry--checked .entry__meta {
  color: var(--p-green-300);
}

.entry__note {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  margin-top: 2px;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.entry__edit {
  flex: 1 1 220px;
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding: 0 var(--jf-space-1) var(--jf-space-1) var(--jf-space-1-5);
}

.entry__notes {
  flex: 1;
  min-width: 0;
}

.remind-button {
  align-self: flex-start;
}

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
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
}

.color-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.color-swatch {
  width: 32px;
  height: 32px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 50%;
  cursor: pointer;
}

.color-swatch--active {
  border-color: var(--jf-color-text);
  box-shadow: 0 0 0 2px var(--jf-color-card) inset;
}

.color-picker {
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: none;
  cursor: pointer;
}

@media (max-width: 767px) {
  .list-head h1 {
    font-size: var(--jf-text-xl);
  }

  .list-head__actions {
    flex: 1 1 100%;
  }

  .list-head__actions > :first-child {
    flex: 1;
  }

  .remind-button {
    align-self: stretch;
  }
}
</style>
