import { defineStore } from 'pinia'
import { ref } from 'vue'
import { publicAdmissionApi } from '@/api/admissions'
import type { PublicAdmissionForm, PublicSealCheck, PublicSubmitResult } from '@/types/admissions'
import { getApiErrorMessage } from '@/utils/apiError'

interface FieldErrors {
  answers?: Record<string, string>
}

/** PDFs go as multipart files (outside the JSON size limit); everything else as JSON. */
function submitBody(extra: Record<string, unknown>, answers: Record<string, unknown>) {
  const files = Object.entries(answers).filter((entry): entry is [string, File] => entry[1] instanceof File)
  const plain = Object.fromEntries(Object.entries(answers).filter(([, value]) => !(value instanceof File)))
  if (!files.length) return { ...extra, answers: plain }
  const body = new FormData()
  body.append('payload', JSON.stringify({ ...extra, answers: plain }))
  for (const [key, file] of files) body.append(`file:${key}`, file, file.name)
  return body
}

/** State of one applicant filling in a form; nothing is kept in browser storage. */
export const usePublicAdmissionStore = defineStore('publicAdmission', () => {
  const code = ref('')
  /** public link instead of a voucher code */
  const slug = ref('')
  const department = ref<number | null>(null)
  /** honeypot; people never see or fill it */
  const website = ref('')
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

  async function openPublic(rawSlug: string) {
    loading.value = true
    error.value = null
    try {
      form.value = (await publicAdmissionApi.publicForm(rawSlug)).data
      slug.value = rawSlug
      code.value = ''
      const choices = form.value.departments ?? []
      department.value = choices.length === 1 ? choices[0]!.id : null
      answers.value = {}
      fieldErrors.value = {}
      result.value = null
    } catch (e) {
      form.value = null
      error.value = getApiErrorMessage(e, 'Dieses Formular ist nicht (mehr) öffentlich.')
    } finally {
      loading.value = false
    }
  }

  function chooseDepartment(id: number | null) {
    department.value = id
  }

  function setWebsite(value: string) {
    website.value = value
  }

  function setAnswers(next: Record<string, unknown>) {
    answers.value = next
  }

  async function submit() {
    loading.value = true
    error.value = null
    fieldErrors.value = {}
    try {
      const body = submitBody(
        slug.value ? { department: department.value, website: website.value } : {},
        answers.value
      )
      result.value = slug.value
        ? (await publicAdmissionApi.submitPublic(slug.value, body)).data
        : (await publicAdmissionApi.submit(code.value, body)).data
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
    slug.value = ''
    department.value = null
    website.value = ''
    form.value = null
    answers.value = {}
    fieldErrors.value = {}
    result.value = null
    error.value = null
  }

  return {
    code,
    slug,
    department,
    website,
    form,
    answers,
    fieldErrors,
    result,
    sealCheck,
    loading,
    error,
    open,
    openPublic,
    chooseDepartment,
    setWebsite,
    setAnswers,
    submit,
    verify,
    reset
  }
})
