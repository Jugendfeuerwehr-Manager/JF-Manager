<template>
  <div class="builder">
    <header class="builder__bar">
      <RouterLink :to="{ name: 'admission-forms' }" class="builder__back"><i class="pi pi-arrow-left" aria-hidden="true"></i> Formulare</RouterLink>
      <div class="builder__title">
        <div class="builder__title-row">
          <h1>{{ store.current?.title ?? 'Formular' }}</h1>
          <span v-if="store.current" class="builder__chip">{{ scopeLabel }}</span>
          <span v-if="store.current" class="builder__chip" :class="{ 'builder__chip--public': store.current.access === 'public' }">
            {{ store.current.access === 'public' ? 'Öffentlich + Voucher' : 'Nur Voucher' }}
          </span>
        </div>
        <p class="builder__status" aria-live="polite">
          <span v-if="store.current?.current_version">Version {{ store.current.current_version.version }} veröffentlicht</span>
          <span v-else>Noch nicht veröffentlicht</span>
          · <span>{{ saveState }}</span>
        </p>
      </div>
      <div class="builder__tools">
        <AdmButton variant="ghost" icon="pi pi-undo" aria-label="Rückgängig (Strg+Z)" :disabled="!store.canUndo || !canEdit" @click="store.undo()" />
        <AdmButton variant="ghost" icon="pi pi-refresh" aria-label="Wiederholen (Strg+Umschalt+Z)" :disabled="!store.canRedo || !canEdit" @click="store.redo()" />
        <AdmButton :icon="mode === 'preview' ? 'pi pi-pencil' : 'pi pi-eye'" @click="toggleMode('preview')">
          {{ mode === 'preview' ? 'Bearbeiten' : 'Vorschau' }}
        </AdmButton>
        <AdmButton icon="pi pi-cog" :aria-pressed="mode === 'settings'" @click="toggleMode('settings')">Zugang &amp; Einstellungen</AdmButton>
        <AdmButton
          v-if="canPublish"
          variant="primary"
          icon="pi pi-send"
          :disabled="!store.current?.has_unpublished_changes || store.saving"
          :title="store.current?.has_unpublished_changes ? '' : 'Keine Änderungen seit der letzten Version'"
          @click="publishOpen = true"
        >
          Veröffentlichen
          <span v-if="issues.length" class="builder__count">{{ issues.length }} offen</span>
        </AdmButton>
      </div>
    </header>

    <p v-if="store.error && !publishOpen" class="builder__error" role="alert">{{ store.error }}</p>
    <p v-if="store.loading" class="builder__state">Lade Formular …</p>

    <template v-else-if="store.current">
      <nav v-if="mode !== 'settings'" class="builder__pages" aria-label="Seiten des Formulars">
        <template v-for="(page, index) in store.draft.pages" :key="page.id">
          <span v-if="index > 0" class="builder__page-sep" aria-hidden="true">›</span>
          <button
            type="button"
            class="builder__page"
            :class="{ 'builder__page--active': index === activePage }"
            :aria-current="index === activePage ? 'step' : undefined"
            @click="selectPage(index)"
          >
            <span class="builder__page-num">{{ index + 1 }}</span>
            {{ page.title || `Seite ${index + 1}` }}
            <span v-if="pageIssues[index]" class="builder__page-dot" :aria-label="`${pageIssues[index]} Hinweise`"></span>
            <span v-else class="builder__page-count">{{ elementCount(index) }}</span>
          </button>
        </template>
        <button v-if="canEdit && mode === 'edit'" type="button" class="builder__page builder__page--add" @click="addPage">+ Seite</button>
      </nav>

      <section v-if="mode === 'preview'" class="builder__preview" aria-label="Vorschau">
        <p class="builder__hint">So sieht das Formular für Antragstellende aus. Rechtstexte erscheinen nach dem Veröffentlichen im Wortlaut.</p>
        <div class="builder__preview-card">
          <FormRenderer v-model="previewAnswers" :schema="store.draft" :page="activePage" id-prefix="preview" />
          <div class="builder__pager">
            <AdmButton icon="pi pi-arrow-left" :disabled="activePage === 0" @click="selectPage(activePage - 1)">Zurück</AdmButton>
            <span>Seite {{ activePage + 1 }} von {{ store.draft.pages.length }}</span>
            <AdmButton icon="pi pi-arrow-right" :disabled="activePage >= store.draft.pages.length - 1" @click="selectPage(activePage + 1)">Weiter</AdmButton>
          </div>
        </div>
      </section>

      <FormSettingsPanel v-else-if="mode === 'settings'" :form="store.current" :can-edit="canEdit" @save="saveSettings" />

      <div v-else class="builder__grid">
        <BuilderPalette
          class="builder__col builder__col--palette"
          :schema="store.draft"
          :references="store.references"
          :disabled="!canEdit"
          :can-create-extra="canCreateExtra"
          @add="addFromPalette"
          @create-extra="extraOpen = true"
          @pick-consent="consentOpen = true"
        />

        <main class="builder__col builder__col--canvas">
          <div v-if="currentPage" class="builder__page-head">
            <div class="builder__page-name">
              <p class="builder__eyebrow">Seite {{ activePage + 1 }} von {{ store.draft.pages.length }}</p>
              <input
                class="builder__page-title"
                :value="currentPage.title"
                aria-label="Titel der Seite"
                placeholder="Seite ohne Titel"
                :readonly="!canEdit"
                @change="renamePage(($event.target as HTMLInputElement).value)"
              />
            </div>
            <div v-if="canEdit" class="builder__page-actions">
              <AdmButton icon="pi pi-arrow-left" aria-label="Seite nach vorn" :disabled="activePage === 0" @click="moveActivePage(-1)" />
              <AdmButton icon="pi pi-arrow-right" aria-label="Seite nach hinten" :disabled="activePage >= store.draft.pages.length - 1" @click="moveActivePage(1)" />
              <AdmButton variant="danger" icon="pi pi-trash" aria-label="Seite entfernen" @click="removePage" />
            </div>
          </div>

          <BuilderCanvas
            :schema="store.draft"
            :active-page="activePage"
            :selected-id="selectedId"
            :issues="issueMap"
            :references="store.references"
            :readonly="!canEdit"
            @select="selectElement"
            @add-section="addSection"
            @rename-section="renameSection"
            @remove-section="removeSection"
          >
            <template #editor="{ element, first, last }">
              <ElementProperties
                :element="element"
                :references="store.references"
                :text-blocks="store.textBlocks"
                :earlier-keys="earlierKeys"
                :used-targets="usedTargets"
                :first="first"
                :last="last"
                :readonly="!canEdit"
                :can-create-consent="canCreateConsent"
                @update="updateSelected"
                @remove="removeSelected"
                @duplicate="duplicateSelected"
                @move="(step) => moveByStep(element.id, step)"
                @done="selectedId = null"
                @create-consent="consentOpen = true"
              />
            </template>
          </BuilderCanvas>

          <div class="builder__next">
            <AdmButton v-if="activePage > 0" icon="pi pi-arrow-left" @click="selectPage(activePage - 1)">
              {{ store.draft.pages[activePage - 1]?.title || 'Vorherige Seite' }}
            </AdmButton>
            <span></span>
            <AdmButton v-if="activePage < store.draft.pages.length - 1" @click="selectPage(activePage + 1)">
              Weiter: {{ store.draft.pages[activePage + 1]?.title || 'Nächste Seite' }} →
            </AdmButton>
          </div>
        </main>

        <aside class="builder__col builder__col--preview" aria-label="Live-Vorschau">
          <p class="builder__eyebrow builder__eyebrow--muted">So sieht es am Handy aus</p>
          <div class="builder__phone">
            <div class="builder__progress" aria-hidden="true">
              <span
                v-for="(page, index) in store.draft.pages"
                :key="page.id"
                :class="{ 'builder__progress--done': index <= activePage }"
              ></span>
            </div>
            <FormRenderer v-model="previewAnswers" :schema="store.draft" :page="activePage" id-prefix="live" />
          </div>
        </aside>
      </div>
    </template>

    <PublishDialog
      :open="publishOpen"
      :next-version="(store.current?.current_version?.version ?? 0) + 1"
      :checks="publishChecks"
      :saving="store.saving"
      :error="store.error"
      @close="publishOpen = false"
      @publish="publish"
    />
    <ConsentKindDialog
      :open="consentOpen"
      :references="store.references"
      :can-create="canCreateConsent"
      @close="consentOpen = false"
      @chosen="insertConsent"
    />
    <MemberFieldDialog
      :open="extraOpen"
      :scopes="extraScopes"
      submit-label="Anlegen und einfügen"
      @close="extraOpen = false"
      @created="insertExtra"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import BuilderCanvas from '@/components/admissions/organisms/BuilderCanvas.vue'
import BuilderPalette from '@/components/admissions/organisms/BuilderPalette.vue'
import ConsentKindDialog from '@/components/admissions/organisms/ConsentKindDialog.vue'
import ElementProperties from '@/components/admissions/organisms/ElementProperties.vue'
import FormRenderer from '@/components/admissions/organisms/FormRenderer.vue'
import FormSettingsPanel from '@/components/admissions/organisms/FormSettingsPanel.vue'
import PublishDialog, { type PublishCheck } from '@/components/admissions/organisms/PublishDialog.vue'
import MemberFieldDialog from '@/components/members/molecules/MemberFieldDialog.vue'
import '@/components/admissions/atoms/admInput.css'
import { useBuilderDragDrop, type DragSource } from '@/composables/useBuilderDragDrop'
import { useAdmissionFormsStore } from '@/stores/admissionForms'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import type { AdmissionFormUpdate, ConsentPerson, ElementLocation, FormElement } from '@/types/admissions'
import type { MemberFieldDefinition } from '@/types/members'
import {
  addPage as addPageTo,
  addSection as addSectionTo,
  allElements,
  cloneSchema,
  createElement,
  elementFromPalette,
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
const LEGAL_PENDING = 'Der Rechtstext ist noch nicht veröffentlicht.'

const route = useRoute()
const store = useAdmissionFormsStore()
const auth = useAuthStore()
const departmentsStore = useDepartmentsStore()

const mode = ref<'edit' | 'preview' | 'settings'>('edit')
const activePage = ref(0)
const selectedId = ref<string | null>(null)
const previewAnswers = ref<Record<string, unknown>>({})
const publishOpen = ref(false)
const consentOpen = ref(false)
const extraOpen = ref(false)
let autosaveTimer: ReturnType<typeof setTimeout> | null = null

const canEdit = computed(() => auth.hasPerm('admissions.change_admissionform'))
const canPublish = computed(() => auth.hasPerm('admissions.publish_admissionform'))
const canCreateExtra = computed(() => auth.hasPerm('members.add_memberfielddefinition'))
const canCreateConsent = computed(
  () => auth.hasPerm('settings_manager.change_privacy_settings') || auth.hasPerm('settings_manager.change_all_settings')
)
const issues = computed(() => store.current?.draft_issues ?? [])
const issueMap = computed(() => issuesByElement(store.draft, issues.value))
const usedTargets = computed(
  () => new Set(allElements(store.draft).filter((element) => element.id !== selectedId.value && element.target).map((element) => element.target!))
)
const currentPage = computed(() => store.draft.pages[activePage.value])
const departmentName = (id: number | null | undefined) =>
  departmentsStore.departments.find((department) => department.id === id)?.name ?? 'Abteilung'
const scopeLabel = computed(() =>
  store.current?.department === null ? 'Organisation · alle Abteilungen' : departmentName(store.current?.department)
)
const extraScopes = computed(() => {
  const organisation = { id: null, name: 'Ganze Organisation (alle Abteilungen)' }
  const department = store.current?.department
  // Organisation forms serve every department, so only organisation-wide fields fit.
  return department === null || department === undefined
    ? [organisation]
    : [organisation, { id: department, name: `Nur ${departmentName(department)}` }]
})
const saveState = computed(() => {
  if (store.saving) return 'Speichert …'
  if (store.dirty) return 'Ungespeicherte Änderungen'
  return store.current?.has_unpublished_changes ? 'Entwurf gespeichert' : 'Alles veröffentlicht'
})

function pageOf(path: string) {
  const match = /^pages\.(\d+)/.exec(path)
  return match ? Number(match[1]) : null
}

const pageIssues = computed(() => {
  const counts: Record<number, number> = {}
  for (const issue of issues.value) {
    const page = pageOf(issue.path)
    if (page !== null) counts[page] = (counts[page] ?? 0) + 1
  }
  return counts
})

function elementCount(page: number) {
  return store.draft.pages[page]?.sections.reduce((sum, section) => sum + section.elements.length, 0) ?? 0
}

function issueLocation(path: string) {
  const match = /^pages\.(\d+)\.sections\.(\d+)\.elements\.(\d+)/.exec(path)
  if (!match) return ''
  const [page, section, index] = match.slice(1).map(Number) as [number, number, number]
  const element = store.draft.pages[page]?.sections[section]?.elements[index]
  const title = store.draft.pages[page]?.title || `Seite ${page + 1}`
  return `Seite ${page + 1} (${title})${element?.label ? ` · „${element.label}“` : ''}`
}

const publishChecks = computed<PublishCheck[]>(() => {
  const checks: PublishCheck[] = issues.value.map((issue) => ({
    ok: false,
    title: issue.message,
    detail: issueLocation(issue.path),
    link:
      issue.message === LEGAL_PENDING
        ? { to: { name: 'settings-privacy' }, label: 'Rechtstexte in den Datenschutz-Einstellungen veröffentlichen' }
        : undefined
  }))
  const elements = allElements(store.draft)
  const member = elements.filter((element) => element.target && !element.target.startsWith('member.extra.')).length
  const extra = elements.filter((element) => element.target?.startsWith('member.extra.')).length
  const consents = elements.filter((element) => element.type === 'consent')
  checks.push({
    ok: true,
    title: 'Alle Angaben landen am Mitglied',
    detail: `${member} Mitgliedsfelder, ${extra} Zusatzfelder${elements.some((element) => element.type === 'guardians') ? ', Sorgeberechtigte' : ''}`
  })
  if (consents.length) {
    checks.push({
      ok: true,
      title: `${consents.length} Einwilligung${consents.length === 1 ? '' : 'en'}`,
      detail: consents.map((element) => element.label).filter(Boolean).join(', ')
    })
  }
  return checks
})

const earlierKeys = computed(() => {
  const keys: string[] = []
  for (const element of allElements(store.draft)) {
    if (element.id === selectedId.value) return keys
    if (element.key && ['checkbox', 'select', 'radio', 'text'].includes(element.type)) keys.push(element.key)
  }
  return keys
})
const selectedLocation = computed(() => (selectedId.value ? locate(store.draft, selectedId.value) : null))

function toggleMode(next: 'preview' | 'settings') {
  mode.value = mode.value === next ? 'edit' : next
}

function selectElement(id: string | null) {
  selectedId.value = id
}

function selectPage(page: number) {
  if (page < 0 || page >= store.draft.pages.length) return
  activePage.value = page
  selectedId.value = null
}

/** Where a click in the palette inserts: behind the open element, else at the end of the page. */
function insertionPoint(): ElementLocation {
  if (!store.draft.pages[activePage.value]) {
    store.edit(addPageTo(store.draft, 'Seite 1'))
    activePage.value = store.draft.pages.length - 1
  }
  const at = selectedLocation.value
  if (at && at.page === activePage.value) return { ...at, index: at.index + 1 }
  const page = store.draft.pages[activePage.value]!
  if (!page.sections.length) store.edit(addSectionTo(store.draft, activePage.value, 'Abschnitt'))
  const section = store.draft.pages[activePage.value]!.sections.length - 1
  return { page: activePage.value, section, index: store.draft.pages[activePage.value]!.sections[section]!.elements.length }
}

function insert(element: FormElement, at: ElementLocation) {
  store.edit(insertElement(store.draft, at, element))
  selectedId.value = element.id
}

function addFromPalette(paletteId: string) {
  const element = elementFromPalette(paletteId, store.draft, store.references)
  if (element) insert(element, insertionPoint())
}

function onDrop(source: DragSource, target: ElementLocation) {
  if (source.kind === 'new') {
    const element = elementFromPalette(source.paletteId, store.draft, store.references)
    if (element) insert(element, target)
    return
  }
  const from = locate(store.draft, source.elementId)
  if (!from) return
  store.edit(moveElement(store.draft, from, target))
  selectedId.value = source.elementId
}

useBuilderDragDrop(onDrop, () => canEdit.value && mode.value === 'edit')

async function insertConsent(choice: { slug: string; label: string; person: ConsentPerson; created: boolean }) {
  if (choice.created) await store.refreshReferences()
  const at = selectedLocation.value
  const selected = at ? store.draft.pages[at.page]?.sections[at.section]?.elements[at.index] : null
  // From the editor of an open consent: fill that one instead of adding another.
  if (selected?.type === 'consent' && !selected.consent_kind) {
    store.edit(updateElement(store.draft, selected.id, { consent_kind: choice.slug, label: choice.label, person: choice.person }))
    return
  }
  const element = { ...createElement('consent', store.draft), consent_kind: choice.slug, label: choice.label, person: choice.person }
  insert(element, insertionPoint())
}

async function insertExtra(definition: MemberFieldDefinition) {
  await store.refreshReferences()
  addFromPalette(`extra:member.extra.${definition.key}`)
}

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
  if (!at) return
  const element = store.draft.pages[at.page]!.sections[at.section]!.elements[at.index]!
  const copy = { ...cloneSchema(element), id: newId(), key: element.key ? `${element.key}_kopie` : undefined }
  insert(copy, { ...at, index: at.index + 1 })
}

function renamePage(title: string) {
  store.edit(renameContainer(store.draft, activePage.value, null, title))
}

function renameSection(section: number, title: string) {
  store.edit(renameContainer(store.draft, activePage.value, section, title))
}

function removeSection(section: number) {
  if (!window.confirm('Soll dieser Abschnitt mit allen Elementen entfernt werden?')) return
  store.edit(removeContainer(store.draft, activePage.value, section))
  selectedId.value = null
}

function removePage() {
  if (!window.confirm('Soll diese Seite mit allen Elementen entfernt werden?')) return
  store.edit(removeContainer(store.draft, activePage.value, null))
  selectedId.value = null
  activePage.value = Math.min(activePage.value, Math.max(store.draft.pages.length - 1, 0))
}

function moveActivePage(step: -1 | 1) {
  const to = activePage.value + step
  store.edit(movePage(store.draft, activePage.value, to))
  if (to >= 0 && to < store.draft.pages.length) activePage.value = to
}

function addPage() {
  store.edit(addPageTo(store.draft, `Seite ${store.draft.pages.length + 1}`))
  selectPage(store.draft.pages.length - 1)
}

function addSection() {
  store.edit(addSectionTo(store.draft, activePage.value))
}

async function saveSettings(data: AdmissionFormUpdate) {
  try {
    const departmentChanged = data.department !== undefined && data.department !== store.current?.department
    await store.saveSettings(data)
    // Another scope offers other additional fields.
    if (departmentChanged) await store.refreshReferences()
  } catch {
    // store.error is shown above
  }
}

async function publish(changeNote: string) {
  try {
    await store.publish(changeNote)
    publishOpen.value = false
  } catch {
    // store.error is shown in the dialog
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
  if (!departmentsStore.departments.length) departmentsStore.fetchDepartments()
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
  flex: 1 1 18rem;
  min-width: 0;
}

.builder__title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
}

.builder__title h1 {
  overflow-wrap: anywhere;
  margin: 0;
  font-size: var(--jf-text-xl);
}

.builder__chip {
  padding: 0.15rem 0.6rem;
  border: 1px solid var(--jf-color-border);
  border-radius: 999px;
  background: var(--jf-color-card);
  white-space: nowrap;
  font-size: var(--jf-text-xs);
}

.builder__chip--public {
  border-color: transparent;
  background: var(--jf-color-success-surface);
  color: var(--jf-color-success);
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

.builder__count {
  margin-left: var(--jf-space-0-5);
  padding: 0 0.45rem;
  border-radius: 999px;
  background: var(--jf-color-card);
  color: var(--jf-color-primary);
  font-size: var(--jf-text-xs);
}

.builder__error {
  margin: 0;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-danger-surface);
  color: var(--jf-color-danger);
}

.builder__pages {
  display: flex;
  align-items: flex-end;
  gap: var(--jf-space-0-5);
  border-bottom: 1px solid var(--jf-color-border);
  overflow-x: auto;
}

.builder__page {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
  padding: 0 var(--jf-space-1-5);
  border: 0;
  border-bottom: 3px solid transparent;
  background: none;
  color: var(--jf-color-text-muted);
  font: inherit;
  white-space: nowrap;
  cursor: pointer;
}

.builder__page:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: -2px;
}

.builder__page--active {
  border-bottom-color: var(--jf-color-primary);
  color: var(--jf-color-text);
  font-weight: var(--jf-weight-semibold);
}

.builder__page--add {
  color: var(--jf-color-primary);
}

.builder__page-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  border: 1px solid var(--jf-color-border);
  border-radius: 50%;
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
}

.builder__page--active .builder__page-num {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.builder__page-count {
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
  font-weight: normal;
}

.builder__page-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--jf-color-warning);
}

.builder__page-sep {
  align-self: center;
  color: var(--jf-color-text-muted);
}

.builder__grid {
  display: grid;
  grid-template-columns: 15rem minmax(0, 1fr) 19rem;
  gap: var(--jf-space-2);
  align-items: start;
}

.builder__col--palette {
  position: sticky;
  top: var(--jf-space-2);
  max-height: calc(100vh - 8rem);
  overflow-y: auto;
}

.builder__col--preview {
  position: sticky;
  top: var(--jf-space-2);
  min-width: 0;
}

.builder__phone :deep(*) {
  overflow-wrap: anywhere;
}

.builder__col--palette {
  padding: var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.builder__col--canvas {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  min-width: 0;
}

.builder__page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.builder__page-name {
  flex: 1 1 16rem;
  min-width: 0;
}

.builder__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--jf-color-primary);
}

.builder__eyebrow--muted {
  color: var(--jf-color-text-muted);
}

.builder__page-title {
  width: 100%;
  min-height: var(--jf-touch-target, 44px);
  padding: 0 var(--jf-space-1);
  margin-left: calc(-1 * var(--jf-space-1));
  border: 1px solid transparent;
  border-radius: var(--jf-radius-md);
  background: none;
  color: var(--jf-color-text);
  font: inherit;
  font-size: var(--jf-text-xl);
  font-weight: var(--jf-weight-semibold);
}

.builder__page-title:hover:not([readonly]),
.builder__page-title:focus-visible {
  border-color: var(--jf-color-border);
  outline: none;
}

.builder__page-actions {
  display: flex;
  gap: var(--jf-space-0-5);
}

.builder__next {
  display: flex;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.builder__phone {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  /* Phone proportions; the page scrolls inside like on a device. */
  height: min(36rem, calc(100vh - 12rem));
  overflow-y: auto;
  overscroll-behavior: contain;
  margin-top: var(--jf-space-1);
  padding: var(--jf-space-2);
  border: 8px solid var(--jf-color-text);
  border-radius: 2rem;
  background: var(--jf-color-card);
  font-size: var(--jf-text-sm);
}

.builder__progress {
  display: flex;
  gap: 4px;
}

.builder__progress span {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: var(--jf-color-border);
}

.builder__progress .builder__progress--done {
  background: var(--jf-color-primary);
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

@media (max-width: 1280px) {
  .builder__grid {
    grid-template-columns: 14rem minmax(0, 1fr);
  }

  .builder__col--preview {
    display: none;
  }
}

@media (max-width: 860px) {
  .builder__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .builder__col--palette {
    position: static;
    max-height: none;
  }
}
</style>
