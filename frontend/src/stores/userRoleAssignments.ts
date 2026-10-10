import { defineStore } from 'pinia'
import { ref } from 'vue'
import { roleAssignmentsApi } from '@/api/role-assignments'
import { getApiErrorMessage } from '@/utils/apiError'
import type { RoleAssignmentInput, RoleAssignmentOptions, RoleAssignmentPreview, RoleExplanation } from '@/types/role-assignments'

export const useUserRoleAssignmentsStore = defineStore('userRoleAssignments', () => {
  const options = ref<RoleAssignmentOptions | null>(null)
  const roles = ref<RoleExplanation[]>([])
  const preview = ref<RoleAssignmentPreview | null>(null)
  const loading = ref(false), reviewing = ref(false), saving = ref(false)
  const error = ref(''), success = ref('')
  let userId: number | null = null, generation = 0, reviewGeneration = 0
  let reviewed: RoleAssignmentInput | null = null

  function discardPreview() {
    reviewGeneration++
    preview.value = null; reviewed = null; reviewing.value = false
  }
  async function load(id: number) {
    const current = ++generation
    userId = id; options.value = null; roles.value = []; error.value = ''; success.value = ''
    discardPreview(); loading.value = true
    try {
      const [choices, explanation] = await Promise.all([roleAssignmentsApi.options(), roleAssignmentsApi.explain(id)])
      if (current === generation) { options.value = choices.data; roles.value = explanation.data.roles }
    } catch (err) {
      if (current === generation) error.value = getApiErrorMessage(err, 'Rollen konnten nicht geladen werden.')
    } finally { if (current === generation) loading.value = false }
  }
  async function review(input: Omit<RoleAssignmentInput, 'user_id'>) {
    if (!userId || loading.value || saving.value) return
    discardPreview()
    const current = reviewGeneration
    const personGeneration = generation
    const request = { ...input, user_id: userId }
    reviewing.value = true; error.value = ''; success.value = ''
    try {
      const response = await roleAssignmentsApi.preview(request)
      if (current === reviewGeneration && personGeneration === generation) { reviewed = request; preview.value = response.data }
    } catch (err) {
      if (current === reviewGeneration && personGeneration === generation) error.value = getApiErrorMessage(err, 'Wirkung konnte nicht geprüft werden.')
    } finally { if (current === reviewGeneration) reviewing.value = false }
  }
  async function save() {
    if (!reviewed || !preview.value?.changed || saving.value) return
    const current = generation
    const request = { ...reviewed, fingerprint: preview.value.fingerprint }
    saving.value = true; error.value = ''
    try {
      const response = await roleAssignmentsApi.apply(request)
      if (current === generation) { roles.value = response.data.roles; discardPreview(); success.value = 'Rollenzuweisung gespeichert.' }
    } catch (err) {
      if (current === generation) { discardPreview(); error.value = getApiErrorMessage(err, 'Speichern fehlgeschlagen. Bitte die Wirkung erneut prüfen.') }
    } finally { saving.value = false }
  }
  function clear() { generation++; userId = null; options.value = null; roles.value = []; discardPreview() }
  return { options, roles, preview, loading, reviewing, saving, error, success, load, review, save, discardPreview, clear }
})
