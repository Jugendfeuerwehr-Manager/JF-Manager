import { defineStore } from 'pinia'
import { ref } from 'vue'
import { publicAdmissionApi } from '@/api/admissions'
import type { PublicAdmissionForm, PublicSealCheck, PublicSubmitResult } from '@/types/admissions'
import { getApiErrorMessage } from '@/utils/apiError'

interface FieldErrors {
  answers?: Record<string, string>
}

/** State of one applicant filling in a form; nothing is kept in browser storage. */
export const usePublicAdmissionStore = defineStore('publicAdmission', () => {
  const code = ref('')
  const form = ref<PublicAdmissionForm | null>(null)
  const answers = ref<Record<string, unknown>>({})
  const fieldErrors = ref<Record<string, string>>({})
  const result = ref<PublicSubmitResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function open(rawCode: string) {
    loading.value = true
    error.value = null
    try {
      form.value = (await publicAdmissionApi.form(rawCode)).data
      code.value = rawCode
      answers.value = { ...form.value.prefill }
      fieldErrors.value = {}
      result.value = null
    } catch (e) {
      form.value = null
      error.value = getApiErrorMessage(e, 'Der Code ist ungültig, abgelaufen oder wurde bereits verwendet.')
    } finally {
      loading.value = false
    }
  }

  function setAnswers(next: Record<string, unknown>) {
    answers.value = next
  }

  async function submit() {
    loading.value = true
    error.value = null
    fieldErrors.value = {}
    try {
      result.value = (await publicAdmissionApi.submit(code.value, answers.value)).data
      return result.value
    } catch (e) {
      const data = (e as { response?: { data?: FieldErrors } }).response?.data
      fieldErrors.value = data?.answers ?? {}
      error.value = Object.keys(fieldErrors.value).length
        ? 'Bitte die markierten Angaben prüfen.'
        : getApiErrorMessage(e, 'Der Antrag konnte nicht gesendet werden.')
      throw e
    } finally {
      loading.value = false
    }
  }

  const sealCheck = ref<PublicSealCheck | null>(null)

  async function verify(publicId: string) {
    loading.value = true
    error.value = null
    sealCheck.value = null
    try {
      sealCheck.value = (await publicAdmissionApi.verify(publicId)).data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Dieses Siegel ist nicht bekannt.')
    } finally {
      loading.value = false
    }
  }

  function reset() {
    code.value = ''
    form.value = null
    answers.value = {}
    fieldErrors.value = {}
    result.value = null
    error.value = null
  }

  return { code, form, answers, fieldErrors, result, sealCheck, loading, error, open, setAnswers, submit, verify, reset }
})
