<template>
  <div class="builder">
    <header class="builder__bar">
      <RouterLink :to="{ name: 'admission-forms' }" class="builder__back"><i class="pi pi-arrow-left" aria-hidden="true"></i> Formulare</RouterLink>
      <div class="builder__title">
        <h1>{{ store.current?.title ?? 'Formular' }}</h1>
        <p class="builder__status" aria-live="polite">
          <span v-if="store.current?.current_version">Veröffentlicht: Version {{ store.current.current_version.version }}</span>
          <span v-else>Noch nicht veröffentlicht</span>
          · <span>{{ saveState }}</span>
        </p>
      </div>
      <div class="builder__tools">
        <AdmButton variant="ghost" icon="pi pi-undo" aria-label="Rückgängig (Strg+Z)" :disabled="!store.canUndo || !canEdit" @click="store.undo()" />
        <AdmButton variant="ghost" icon="pi pi-refresh" aria-label="Wiederholen (Strg+Umschalt+Z)" :disabled="!store.canRedo || !canEdit" @click="store.redo()" />
        <AdmButton :icon="mode === 'preview' ? 'pi pi-pencil' : 'pi pi-eye'" @click="mode = mode === 'preview' ? 'edit' : 'preview'">
          {{ mode === 'preview' ? 'Bearbeiten' : 'Vorschau' }}
        </AdmButton>
        <AdmButton icon="pi pi-cog" :aria-pressed="mode === 'settings'" @click="mode = mode === 'settings' ? 'edit' : 'settings'">Einstellungen</AdmButton>
        <AdmButton
          v-if="canPublish"
          variant="primary"
          icon="pi pi-send"
          :disabled="!!issues.length || !store.current?.has_unpublished_changes || store.saving"
          :title="issues.length ? 'Erst die markierten Hinweise beheben' : ''"
          @click="openPublish"
        >
          Veröffentlichen
        </AdmButton>
      </div>
    </header>

    <p v-if="store.error" class="builder__error" role="alert">{{ store.error }}</p>
    <p v-if="store.loading" class="builder__state">Lade Formular …</p>

    <section v-else-if="mode === 'preview'" class="builder__preview" aria-label="Vorschau">
      <p class="builder__hint">So sieht das Formular für Antragstellende aus. Rechtstexte erscheinen nach dem Veröffentlichen im Wortlaut.</p>
      <div class="builder__preview-card">
        <FormRenderer v-model="previewAnswers" :schema="store.draft" :page="previewPage" id-prefix="preview" />
        <div class="builder__pager">
          <AdmButton icon="pi pi-arrow-left" :disabled="previewPage === 0" @click="previewPage--">Zurück</AdmButton>
          <span>Seite {{ previewPage + 1 }} von {{ store.draft.pages.length }}</span>
          <AdmButton icon="pi pi-arrow-right" :disabled="previewPage >= store.draft.pages.length - 1" @click="previewPage++">Weiter</AdmButton>
        </div>
      </div>
    </section>

    <FormSettingsPanel v-else-if="mode === 'settings' && store.current" :form="store.current" :can-edit="canEdit" @save="saveSettings" />

    <div v-else class="builder__grid">
      <BuilderPalette class="builder__col builder__col--palette" :disabled="!canEdit" @add="addAtSelection" />
      <main class="builder__col builder__col--canvas">
        <BuilderCanvas
          :schema="store.draft"
          :active-page="activePage"
          :selected-id="selectedId"
          :selected-section="selectedSection"
          :issues="issueMap"
          :readonly="!canEdit"
          @select="selectElement"
          @select-page="selectPage"
          @select-section="selectSection"
          @move="moveByStep"
          @add-page="addPage"
          @add-section="addSection"
        />
        <section v-if="issues.length" class="builder__issues" aria-labelledby="issues-title">
          <h2 id="issues-title">Vor dem Veröffentlichen beheben ({{ issues.length }})</h2>
          <ul>
            <li v-for="issue in issues" :key="issue.path + issue.message">{{ issue.message }}</li>
          </ul>
        </section>
      </main>
      <ElementProperties
        class="builder__col builder__col--props"
        :element="selectedElement"
        :container="selectedContainer"
        :references="store.references"
        :text-blocks="store.textBlocks"
        :earlier-keys="earlierKeys"
        :readonly="!canEdit"
        @update="updateSelected"
        @remove="removeSelected"
        @duplicate="duplicateSelected"
        @rename="renameSelected"
        @remove-container="removeSelectedContainer"
        @move-page="(step) => moveActivePage(step)"
      />
    </div>

    <dialog ref="publishDialog" class="builder__dialog" aria-labelledby="publish-title" @close="changeNote = ''">
      <form method="dialog" class="builder__dialog-body" @submit.prevent="publish">
        <h2 id="publish-title">Formular veröffentlichen</h2>
        <p>Neue Anträge verwenden ab sofort diese Version. Bereits eingereichte Anträge behalten ihre Fassung.</p>
        <AdmField input-id="change-note" label="Änderungshinweis (optional)">
          <input id="change-note" v-model="changeNote" class="adm-input" maxlength="300" />
        </AdmField>
        <div class="builder__dialog-actions">
          <AdmButton variant="ghost" @click="publishDialog?.close()">Abbrechen</AdmButton>
          <AdmButton variant="primary" type="submit" icon="pi pi-send" :loading="store.saving">Veröffentlichen</AdmButton>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import AdmField from '@/components/admissions/atoms/AdmField.vue'
import BuilderCanvas from '@/components/admissions/organisms/BuilderCanvas.vue'
import BuilderPalette from '@/components/admissions/organisms/BuilderPalette.vue'
import ElementProperties from '@/components/admissions/organisms/ElementProperties.vue'
import FormRenderer from '@/components/admissions/organisms/FormRenderer.vue'
import FormSettingsPanel from '@/components/admissions/organisms/FormSettingsPanel.vue'
import '@/components/admissions/atoms/admInput.css'
import { useBuilderDragDrop, type DragSource } from '@/composables/useBuilderDragDrop'
import { useAdmissionFormsStore } from '@/stores/admissionForms'
import { useAuthStore } from '@/stores/auth'
import type { AdmissionFormUpdate, ElementLocation, ElementType, FormElement } from '@/types/admissions'
import {
  addPage as addPageTo,
  addSection as addSectionTo,
  createElement,
  insertElement,
  issuesByElement,
  locate,
  moveElement,
  movePage,
  newId,
  removeContainer,
  removeElement,
  renameContainer,
  updateElement
} from '@/utils/admissionSchema'

const AUTOSAVE_MS = 1200

const route = useRoute()
const store = useAdmissionFormsStore()
const auth = useAuthStore()

const mode = ref<'edit' | 'preview' | 'settings'>('edit')
const activePage = ref(0)
const selectedId = ref<string | null>(null)
const selectedSection = ref<number | null>(null)
const pageSelected = ref(false)
const previewAnswers = ref<Record<string, unknown>>({})
const previewPage = ref(0)
const changeNote = ref('')
const publishDialog = ref<HTMLDialogElement | null>(null)
let autosaveTimer: ReturnType<typeof setTimeout> | null = null

const canEdit = computed(() => auth.hasPerm('admissions.change_admissionform'))
const canPublish = computed(() => auth.hasPerm('admissions.publish_admissionform'))
const issues = computed(() => store.current?.draft_issues ?? [])
const issueMap = computed(() => issuesByElement(store.draft, issues.value))
const saveState = computed(() => {
  if (store.saving) return 'Speichert …'
  if (store.dirty) return 'Ungespeicherte Änderungen'
  return store.current?.has_unpublished_changes ? 'Entwurf gespeichert' : 'Alles veröffentlicht'
})

const selectedLocation = computed(() => (selectedId.value ? locate(store.draft, selectedId.value) : null))
const selectedElement = computed<FormElement | null>(() => {
  const at = selectedLocation.value
  return at ? (store.draft.pages[at.page]?.sections[at.section]?.elements[at.index] ?? null) : null
})
const selectedContainer = computed(() => {
  const page = store.draft.pages[activePage.value]
  if (!page || selectedId.value) return null
  if (pageSelected.value) return { kind: 'page' as const, title: page.title }
  const section = selectedSection.value === null ? undefined : page.sections[selectedSection.value]
  return section ? { kind: 'section' as const, title: section.title } : null
})
const earlierKeys = computed(() => {
  const keys: string[] = []
  for (const page of store.draft.pages) {
    for (const section of page.sections) {
      for (const element of section.elements) {
        if (element.id === selectedId.value) return keys
        if (element.key && ['checkbox', 'select', 'radio', 'text'].includes(element.type)) keys.push(element.key)
      }
    }
  }
  return keys
})

function selectElement(id: string) {
  selectedId.value = id
  pageSelected.value = false
  const at = locate(store.draft, id)
  if (at) selectedSection.value = at.section
}

function selectPage(page: number) {
  if (page === activePage.value) {
    selectedId.value = null
    pageSelected.value = true
    return
  }
  activePage.value = page
  selectedId.value = null
  selectedSection.value = 0
  pageSelected.value = false
}

function selectSection(section: number) {
  selectedId.value = null
  pageSelected.value = false
  selectedSection.value = section
}

function insertAt(type: ElementType, at: ElementLocation) {
  const element = createElement(type, store.draft)
  store.edit(insertElement(store.draft, at, element))
  selectElement(element.id)
}

function addAtSelection(type: ElementType) {
  const page = store.draft.pages[activePage.value]
  if (!page) {
    store.edit(addPageTo(store.draft))
    activePage.value = store.draft.pages.length - 1
  }
  const current = store.draft.pages[activePage.value]!
  const at = selectedLocation.value
  if (at && at.page === activePage.value) return insertAt(type, { ...at, index: at.index + 1 })
  const section = Math.min(selectedSection.value ?? current.sections.length - 1, current.sections.length - 1)
  if (section < 0) {
    store.edit(addSectionTo(store.draft, activePage.value))
    return insertAt(type, { page: activePage.value, section: 0, index: 0 })
  }
  insertAt(type, { page: activePage.value, section, index: current.sections[section]!.elements.length })
}

function onDrop(source: DragSource, target: ElementLocation) {
  if (source.kind === 'new') return insertAt(source.type, target)
  const from = locate(store.draft, source.elementId)
  if (!from) return
  store.edit(moveElement(store.draft, from, target))
  selectElement(source.elementId)
}

useBuilderDragDrop(onDrop, () => canEdit.value && mode.value === 'edit')

function moveByStep(elementId: string, step: -1 | 1) {
  const from = locate(store.draft, elementId)
  if (!from) return
  // Moving down by one means inserting behind the next element.
  const index = step === 1 ? from.index + 2 : from.index - 1
  store.edit(moveElement(store.draft, from, { ...from, index: Math.max(index, 0) }))
}

function updateSelected(patch: Partial<FormElement>) {
  if (!selectedId.value) return
  store.edit(updateElement(store.draft, selectedId.value, patch))
}

function removeSelected() {
  const at = selectedLocation.value
  if (!at) return
  store.edit(removeElement(store.draft, at))
  selectedId.value = null
}

function duplicateSelected() {
  const at = selectedLocation.value
  const element = selectedElement.value
  if (!at || !element) return
  const copy = { ...structuredClone(element), id: newId(), key: element.key ? `${element.key}_kopie` : undefined }
  store.edit(insertElement(store.draft, { ...at, index: at.index + 1 }, copy))
  selectElement(copy.id)
}

function renameSelected(title: string) {
  const section = pageSelected.value ? null : selectedSection.value
  store.edit(renameContainer(store.draft, activePage.value, section, title))
}

function removeSelectedContainer() {
  const section = pageSelected.value ? null : selectedSection.value
  const label = section === null ? 'diese Seite' : 'diesen Abschnitt'
  if (!window.confirm(`Soll ${label} mit allen Elementen entfernt werden?`)) return
  store.edit(removeContainer(store.draft, activePage.value, section))
  pageSelected.value = false
  selectedSection.value = null
  activePage.value = Math.min(activePage.value, Math.max(store.draft.pages.length - 1, 0))
}

function moveActivePage(step: -1 | 1) {
  const to = activePage.value + step
  store.edit(movePage(store.draft, activePage.value, to))
  if (to >= 0 && to < store.draft.pages.length) activePage.value = to
}

function addPage() {
  store.edit(addPageTo(store.draft))
  selectPage(store.draft.pages.length - 1)
}

function addSection() {
  store.edit(addSectionTo(store.draft, activePage.value))
  selectSection(store.draft.pages[activePage.value]!.sections.length - 1)
}

async function saveSettings(data: AdmissionFormUpdate) {
  try {
    await store.saveSettings(data)
  } catch {
    // store.error is shown above
  }
}

function openPublish() {
  publishDialog.value?.showModal()
}

async function publish() {
  try {
    await store.publish(changeNote.value)
    publishDialog.value?.close()
  } catch {
    // store.error is shown above
  }
}

watch(
  () => store.draft,
  () => {
    if (!store.dirty) return
    if (autosaveTimer) clearTimeout(autosaveTimer)
    autosaveTimer = setTimeout(() => store.saveDraft().catch(() => undefined), AUTOSAVE_MS)
  }
)

function onKey(event: KeyboardEvent) {
  if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 'z' || mode.value !== 'edit') return
  const target = event.target as HTMLElement
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
  event.preventDefault()
  if (event.shiftKey) store.redo()
  else store.undo()
}

function beforeUnload(event: BeforeUnloadEvent) {
  if (!store.dirty) return
  event.preventDefault()
}

onBeforeRouteLeave(async () => {
  if (!store.dirty) return true
  try {
    await store.saveDraft()
    return true
  } catch {
    return window.confirm('Der Entwurf konnte nicht gespeichert werden. Trotzdem verlassen?')
  }
})

onMounted(() => {
  store.openForm(Number(route.params.id))
  window.addEventListener('keydown', onKey)
  window.addEventListener('beforeunload', beforeUnload)
})

onBeforeUnmount(() => {
  if (autosaveTimer) clearTimeout(autosaveTimer)
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('beforeunload', beforeUnload)
})
</script>

<style scoped>
.builder {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  font-family: var(--jf-font-sans);
  color: var(--jf-color-text);
}

.builder__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-2);
}

.builder__back {
  color: var(--jf-color-text-muted);
  text-decoration: none;
}

.builder__title {
  flex: 1;
  min-width: 12rem;
}

.builder__title h1 {
  margin: 0;
  font-size: var(--jf-text-xl);
}

.builder__status,
.builder__hint,
.builder__state {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.builder__tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5);
}

.builder__error {
  margin: 0;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: #fef2f2;
  color: #991b1b;
}

.builder__grid {
  display: grid;
  grid-template-columns: 15rem minmax(0, 1fr) 20rem;
  gap: var(--jf-space-2);
  align-items: start;
}

.builder__col--palette,
.builder__col--props {
  position: sticky;
  top: var(--jf-space-2);
  max-height: calc(100vh - 8rem);
  overflow-y: auto;
  padding: var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.builder__issues {
  margin-top: var(--jf-space-2);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border-radius: var(--jf-radius-md);
  background: #fffbeb;
  color: #92400e;
}

.builder__issues h2 {
  margin: 0 0 var(--jf-space-0-5);
  font-size: var(--jf-text-md);
}

.builder__issues ul {
  margin: 0;
  padding-left: 1.2rem;
}

.builder__preview-card {
  max-width: 44rem;
  margin: 0 auto;
  padding: var(--jf-space-3);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.builder__pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
  margin-top: var(--jf-space-3);
}

.builder__dialog {
  max-width: 32rem;
  width: calc(100vw - 2rem);
  padding: 0;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
}

.builder__dialog::backdrop {
  background: rgb(0 0 0 / 40%);
}

.builder__dialog-body {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-3);
}

.builder__dialog-body h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
}

.builder__dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}

@media (max-width: 1100px) {
  .builder__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .builder__col--palette,
  .builder__col--props {
    position: static;
    max-height: none;
  }
}
</style>
