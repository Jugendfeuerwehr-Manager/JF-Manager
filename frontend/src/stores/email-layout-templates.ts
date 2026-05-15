import { ref } from 'vue'
import { defineStore } from 'pinia'
import { emailLayoutTemplatesApi } from '@/api/email-layout-templates'
import type { EmailLayoutTemplate, EmailLayoutTemplateUpdate } from '@/types/email-layout-templates'

export const useEmailLayoutTemplatesStore = defineStore('emailLayoutTemplates', () => {
  const templates = ref<EmailLayoutTemplate[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  async function fetchTemplates() {
    loading.value = true
    error.value = null
    try {
      const response = await emailLayoutTemplatesApi.list()
      templates.value = response.data
    } catch (err) {
      error.value = 'Layout-Vorlagen konnten nicht geladen werden.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTemplate(layoutType: string, data: EmailLayoutTemplateUpdate) {
    saving.value = true
    error.value = null
    try {
      const response = await emailLayoutTemplatesApi.update(layoutType, data)
      const idx = templates.value.findIndex((t) => t.layout_type === layoutType)
      if (idx !== -1) {
        templates.value[idx] = response.data
      }
      return response.data
    } catch (err) {
      error.value = 'Layout-Vorlage konnte nicht gespeichert werden.'
      throw err
    } finally {
      saving.value = false
    }
  }

  async function resetTemplate(layoutType: string) {
    saving.value = true
    error.value = null
    try {
      const response = await emailLayoutTemplatesApi.reset(layoutType)
      const idx = templates.value.findIndex((t) => t.layout_type === layoutType)
      if (idx !== -1) {
        templates.value[idx] = response.data
      }
      return response.data
    } catch (err) {
      error.value = 'Layout-Vorlage konnte nicht zurückgesetzt werden.'
      throw err
    } finally {
      saving.value = false
    }
  }

  return { templates, loading, saving, error, fetchTemplates, updateTemplate, resetTemplate }
})
