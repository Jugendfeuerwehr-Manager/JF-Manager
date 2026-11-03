import { defineStore } from 'pinia'
import { ref } from 'vue'
import { admissionVouchersApi, applicationsApi, meetingsApi } from '@/api/admissions'
import type {
  AdmissionVoucher,
  ApplicationDetail,
  ApplicationListItem,
  ApplicationStatus,
  ApplicationVerification,
  CommitteeMeeting,
  CreatedVoucher,
  DecisionInput,
  ParentSuggestion,
  TakeOverInput,
  VoucherCreate
} from '@/types/admissions'
import { getApiErrorMessage } from '@/utils/apiError'

export const useAdmissionsStore = defineStore('admissions', () => {
  const applications = ref<ApplicationListItem[]>([])
  const current = ref<ApplicationDetail | null>(null)
  const verification = ref<ApplicationVerification | null>(null)
  const parentSuggestions = ref<ParentSuggestion[][]>([])
  const vouchers = ref<AdmissionVoucher[]>([])
  const meetings = ref<CommitteeMeeting[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  async function run<T>(task: () => Promise<T>, message: string, flag = loading): Promise<T> {
    flag.value = true
    error.value = null
    try {
      return await task()
    } catch (e) {
      error.value = getApiErrorMessage(e, message)
      throw e
    } finally {
      flag.value = false
    }
  }

  async function fetchApplications(params?: { status?: ApplicationStatus; search?: string }) {
    await run(async () => {
      applications.value = (await applicationsApi.list({ ...params, limit: 200 })).data.results
    }, 'Anträge konnten nicht geladen werden').catch(() => undefined)
  }

  async function openApplication(id: number) {
    await run(async () => {
      const [detail, check, suggestions] = await Promise.all([
        applicationsApi.get(id),
        applicationsApi.verify(id),
        applicationsApi.parentSuggestions(id)
      ])
      current.value = detail.data
      verification.value = check.data
      parentSuggestions.value = suggestions.data
    }, 'Antrag konnte nicht geladen werden').catch(() => undefined)
  }

  async function decide(id: number, data: DecisionInput) {
    return run(async () => {
      current.value = (await applicationsApi.decide(id, data)).data
      verification.value = (await applicationsApi.verify(id)).data
      return current.value
    }, 'Beschluss konnte nicht gespeichert werden', saving)
  }

  async function takeOver(id: number, data: TakeOverInput) {
    return run(async () => {
      const result = (await applicationsApi.takeOver(id, data)).data
      current.value = (await applicationsApi.get(id)).data
      return result.member
    }, 'Antrag konnte nicht übernommen werden', saving)
  }

  async function exportSealed(id: number) {
    return run(async () => {
      const data = (await applicationsApi.exportSealed(id)).data
      verification.value = (await applicationsApi.verify(id)).data
      return data
    }, 'Export fehlgeschlagen', saving)
  }

  async function fetchVouchers(form?: number) {
    await run(async () => {
      vouchers.value = (await admissionVouchersApi.list({ form, limit: 200 })).data.results
    }, 'Voucher konnten nicht geladen werden').catch(() => undefined)
  }

  async function createVoucher(data: VoucherCreate): Promise<CreatedVoucher> {
    return run(async () => {
      const created = (await admissionVouchersApi.create(data)).data
      vouchers.value = [created, ...vouchers.value]
      return created
    }, 'Voucher konnte nicht erstellt werden', saving)
  }

  async function revokeVoucher(id: number) {
    return run(async () => {
      const revoked = (await admissionVouchersApi.revoke(id)).data
      vouchers.value = vouchers.value.map((voucher) => (voucher.id === id ? revoked : voucher))
    }, 'Voucher konnte nicht widerrufen werden', saving)
  }

  async function fetchMeetings() {
    await run(async () => {
      meetings.value = (await meetingsApi.list({ limit: 200 })).data.results
    }, 'Sitzungen konnten nicht geladen werden').catch(() => undefined)
  }

  async function createMeeting(data: Pick<CommitteeMeeting, 'department' | 'body' | 'date' | 'protocol_ref' | 'note'>) {
    return run(async () => {
      const meeting = (await meetingsApi.create(data)).data
      meetings.value = [meeting, ...meetings.value]
      return meeting
    }, 'Sitzung konnte nicht angelegt werden', saving)
  }

  async function decideInMeeting(id: number, data: DecisionInput & { applications: number[] }) {
    return run(async () => {
      await meetingsApi.decide(id, data)
      meetings.value = (await meetingsApi.list({ limit: 200 })).data.results
      applications.value = (await applicationsApi.list({ limit: 200 })).data.results
    }, 'Beschlüsse konnten nicht gespeichert werden', saving)
  }

  return {
    applications,
    current,
    verification,
    parentSuggestions,
    vouchers,
    meetings,
    loading,
    saving,
    error,
    fetchApplications,
    openApplication,
    decide,
    takeOver,
    exportSealed,
    fetchVouchers,
    createVoucher,
    revokeVoucher,
    fetchMeetings,
    createMeeting,
    decideInMeeting
  }
})
