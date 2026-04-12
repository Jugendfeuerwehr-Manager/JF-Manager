/**
 * Pinia Store for Email Templates
 * Manages email template state and operations
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { emailTemplatesApi } from '@/api/email-templates'
import type {
  EmailTemplateList,
  EmailTemplate,
  EmailTemplateCreateUpdate,
  TemplateType,
  AllTemplateVariables,
  TemplatePreviewRequest,
  TemplatePreviewResponse,
  TemplateVariable
} from '@/types/email-templates'
import { getApiErrorMessage } from '@/utils/apiError'

export const useEmailTemplatesStore = defineStore('emailTemplates', () => {
  // State
  const templates = ref<EmailTemplateList[]>([])
  const currentTemplate = ref<EmailTemplate | null>(null)
  const templateTypes = ref<TemplateType[]>([])
  const allVariables = ref<AllTemplateVariables>({})
  const loading = ref(false)
  const saving = ref(false)
  const previewing = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const hasTemplates = computed(() => templates.value.length > 0)
  
  const activeTemplates = computed(() => 
    templates.value.filter(t => t.is_active)
  )
  
  const templateTypeOptions = computed(() => 
    templateTypes.value.map(t => ({ label: t.label, value: t.value }))
  )

  // Actions
  async function fetchTemplates() {
    loading.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.list()
      templates.value = response.data.results
      return templates.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der E-Mail-Vorlagen')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTemplate(id: number) {
    loading.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.get(id)
      currentTemplate.value = response.data
      return currentTemplate.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der E-Mail-Vorlage')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTemplate(data: EmailTemplateCreateUpdate) {
    saving.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.create(data)
      templates.value.push(response.data)
      currentTemplate.value = response.data
      return currentTemplate.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Erstellen der E-Mail-Vorlage')
      throw err
    } finally {
      saving.value = false
    }
  }

  async function updateTemplate(id: number, data: EmailTemplateCreateUpdate) {
    saving.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.update(id, data)
      const index = templates.value.findIndex(t => t.id === id)
      if (index !== -1) {
        templates.value[index] = response.data
      }
      currentTemplate.value = response.data
      return currentTemplate.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Aktualisieren der E-Mail-Vorlage')
      throw err
    } finally {
      saving.value = false
    }
  }

  async function patchTemplate(id: number, data: Partial<EmailTemplateCreateUpdate>) {
    saving.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.patch(id, data)
      const index = templates.value.findIndex(t => t.id === id)
      if (index !== -1) {
        templates.value[index] = response.data
      }
      currentTemplate.value = response.data
      return currentTemplate.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Aktualisieren der E-Mail-Vorlage')
      throw err
    } finally {
      saving.value = false
    }
  }

  async function deleteTemplate(id: number) {
    saving.value = true
    error.value = null
    try {
      await emailTemplatesApi.delete(id)
      templates.value = templates.value.filter(t => t.id !== id)
      if (currentTemplate.value?.id === id) {
        currentTemplate.value = null
      }
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Löschen der E-Mail-Vorlage')
      throw err
    } finally {
      saving.value = false
    }
  }

  async function fetchTemplateTypes() {
    loading.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.getTypes()
      templateTypes.value = response.data
      return templateTypes.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Vorlagentypen')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAllVariables() {
    loading.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.getVariables()
      allVariables.value = response.data as AllTemplateVariables
      return allVariables.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Vorlagenvariablen')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchVariablesForType(templateType: string) {
    loading.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.getVariables(templateType)
      const data = response.data as { template_type: string; variables: TemplateVariable[]; sample_data: Record<string, unknown> }
      return {
        variables: data.variables,
        sample_data: data.sample_data
      }
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Vorlagenvariablen')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function previewTemplate(data: TemplatePreviewRequest): Promise<TemplatePreviewResponse> {
    previewing.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.preview(data)
      return response.data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler bei der Vorschau')
      throw err
    } finally {
      previewing.value = false
    }
  }

  async function fetchDefaultContent(templateType: string) {
    loading.value = true
    error.value = null
    try {
      const response = await emailTemplatesApi.getDefaultContent(templateType)
      return response.data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden des Standard-Templates')
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearCurrentTemplate() {
    currentTemplate.value = null
  }

  return {
    // State
    templates,
    currentTemplate,
    templateTypes,
    allVariables,
    loading,
    saving,
    previewing,
    error,
    
    // Computed
    hasTemplates,
    activeTemplates,
    templateTypeOptions,
    
    // Actions
    fetchTemplates,
    fetchTemplate,
    createTemplate,
    updateTemplate,
    patchTemplate,
    deleteTemplate,
    fetchTemplateTypes,
    fetchAllVariables,
    fetchVariablesForType,
    previewTemplate,
    fetchDefaultContent,
    clearError,
    clearCurrentTemplate
  }
})
