import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { admissionFormsApi, admissionTextBlocksApi } from '@/api/admissions'
import type {
  AdmissionForm,
  AdmissionFormCreate,
  AdmissionFormUpdate,
  AdmissionFormVersion,
  AdmissionTextBlock,
  BuilderReferences,
  FormSchema
} from '@/types/admissions'
import { getApiErrorMessage } from '@/utils/apiError'
import { cloneSchema } from '@/utils/admissionSchema'

const HISTORY_LIMIT = 100

export const useAdmissionFormsStore = defineStore('admissionForms', () => {
  const forms = ref<AdmissionForm[]>([])
  const current = ref<AdmissionForm | null>(null)
  const versions = ref<AdmissionFormVersion[]>([])
  const references = ref<BuilderReferences | null>(null)
  const textBlocks = ref<AdmissionTextBlock[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  // Draft editing with undo/redo; the server copy is ``current.draft_schema``.
  const draft = ref<FormSchema>({ pages: [] })
  const past = ref<FormSchema[]>([])
  const future = ref<FormSchema[]>([])
  const dirty = ref(false)

  const canUndo = computed(() => past.value.length > 0)
  const canRedo = computed(() => future.value.length > 0)

  async function fetchForms(params?: { department?: number }) {
    loading.value = true
    error.value = null
    try {
      forms.value = (await admissionFormsApi.list({ ...params, limit: 200 })).data.results
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Formulare konnten nicht geladen werden')
    } finally {
      loading.value = false
    }
  }

  function adopt(form: AdmissionForm) {
    current.value = form
    draft.value = cloneSchema(form.draft_schema)
    past.value = []
    future.value = []
    dirty.value = false
  }

  async function openForm(id: number) {
    loading.value = true
    error.value = null
    try {
      // References depend on the form: organisation forms only offer organisation-wide fields.
      const [form, refs, blocks] = await Promise.all([
        admissionFormsApi.get(id),
        admissionFormsApi.references(id),
        admissionTextBlocksApi.list()
      ])
      references.value = refs.data
      textBlocks.value = blocks.data.results
      adopt(form.data)
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Formular konnte nicht geladen werden')
    } finally {
      loading.value = false
    }
  }

  async function refreshReferences() {
    if (!current.value) return
    try {
      references.value = (await admissionFormsApi.references(current.value.id)).data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Bausteine konnten nicht geladen werden')
    }
  }

  async function createForm(data: AdmissionFormCreate) {
    error.value = null
    try {
      const form = (await admissionFormsApi.create(data)).data
      forms.value = [...forms.value, form]
      return form
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Formular konnte nicht angelegt werden')
      throw e
    }
  }

  function edit(next: FormSchema) {
    if (next === draft.value) return
    past.value = [...past.value.slice(-HISTORY_LIMIT + 1), draft.value]
    future.value = []
    draft.value = next
    dirty.value = true
  }

  function undo() {
    const previous = past.value.at(-1)
    if (!previous) return
    future.value = [draft.value, ...future.value]
    past.value = past.value.slice(0, -1)
    draft.value = previous
    dirty.value = true
  }

  function redo() {
    const next = future.value[0]
    if (!next) return
    past.value = [...past.value, draft.value]
    future.value = future.value.slice(1)
    draft.value = next
    dirty.value = true
  }

  async function saveSettings(data: AdmissionFormUpdate) {
    if (!current.value) return
    return persist({ ...data })
  }

  async function saveDraft() {
    if (!current.value || !dirty.value) return current.value
    return persist({ draft_schema: draft.value })
  }

  async function persist(data: AdmissionFormUpdate) {
    if (!current.value) return
    saving.value = true
    error.value = null
    try {
      const saved = (await admissionFormsApi.update(current.value.id, data)).data
      current.value = saved
      if ('draft_schema' in data) dirty.value = false
      forms.value = forms.value.map((form) => (form.id === saved.id ? saved : form))
      return saved
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Formular konnte nicht gespeichert werden')
      throw e
    } finally {
      saving.value = false
    }
  }

  async function publish(changeNote = '') {
    if (!current.value) return
    await saveDraft()
    saving.value = true
    error.value = null
    try {
      const version = (await admissionFormsApi.publish(current.value.id, changeNote)).data
      current.value = (await admissionFormsApi.get(current.value.id)).data
      versions.value = [version, ...versions.value]
      return version
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Formular konnte nicht veröffentlicht werden')
      throw e
    } finally {
      saving.value = false
    }
  }

  async function fetchVersions() {
    if (!current.value) return
    try {
      versions.value = (await admissionFormsApi.versions(current.value.id)).data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Versionen konnten nicht geladen werden')
    }
  }

  return {
    forms,
    current,
    versions,
    references,
    textBlocks,
    loading,
    saving,
    error,
    draft,
    dirty,
    canUndo,
    canRedo,
    fetchForms,
    openForm,
    refreshReferences,
    createForm,
    edit,
    undo,
    redo,
    saveSettings,
    saveDraft,
    publish,
    fetchVersions
  }
})
