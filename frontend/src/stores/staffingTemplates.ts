import { defineStore } from 'pinia'
import { ref } from 'vue'
import { staffingTemplatesApi, type StaffingTemplate, type StaffingTemplateInput } from '@/api/participation'
import { getApiErrorMessage } from '@/utils/apiError'

/** Besetzungsvorlagen (PART-04.5): list, save from a service, archive. Applying lives in the participation store. */
export const useStaffingTemplatesStore = defineStore('staffingTemplates', () => {
  const templates = ref<StaffingTemplate[]>([])
  const canManageOrganization = ref(false)
  const loading = ref(false)
  const busy = ref(false)
  const error = ref<string | null>(null)
  const department = ref<number | null>(null)
  const showArchived = ref(false)

  async function load(dept: number | null = department.value, archived = showArchived.value) {
    department.value = dept
    showArchived.value = archived
    loading.value = true
    error.value = null
    try {
      const { data } = await staffingTemplatesApi.list({ department: dept, archived })
      templates.value = data.results
      canManageOrganization.value = data.can_manage_organization
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Die Besetzungsvorlagen konnten nicht geladen werden.')
    } finally {
      loading.value = false
    }
  }

  async function create(input: StaffingTemplateInput): Promise<StaffingTemplate | null> {
    busy.value = true
    error.value = null
    try {
      const { data } = await staffingTemplatesApi.create(input)
      await load()
      return data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Die Vorlage konnte nicht gespeichert werden.')
      return null
    } finally {
      busy.value = false
    }
  }

  async function setArchived(template: StaffingTemplate, archived: boolean): Promise<boolean> {
    busy.value = true
    error.value = null
    try {
      await staffingTemplatesApi.archive(template.id, archived)
      await load()
      return true
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Die Vorlage konnte nicht geändert werden.')
      return false
    } finally {
      busy.value = false
    }
  }

  return { templates, canManageOrganization, loading, busy, error, department, showArchived, load, create, setArchived }
})
