import { defineStore } from 'pinia'
import { ref } from 'vue'
import { annualReportApi } from '@/api/membership'
import type { AnnualReportResponse, ReportManual, StatisticsProfile } from '@/types/membership'
import { getApiErrorMessage } from '@/utils/apiError'

export const useAnnualReportStore = defineStore('annualReport', () => {
  const report = ref<AnnualReportResponse | null>(null)
  const profile = ref<StatisticsProfile | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  async function load(department: number, year: number) {
    loading.value = true
    error.value = null
    try {
      const [preview, profiles] = await Promise.all([
        annualReportApi.preview(department, year),
        annualReportApi.profiles(department)
      ])
      report.value = preview.data
      profile.value = profiles.data.results[0] ?? null
    } catch (e) {
      report.value = null
      error.value = getApiErrorMessage(e, 'Jahresmeldung konnte nicht berechnet werden')
    } finally {
      loading.value = false
    }
  }

  async function act(task: () => Promise<void>, message: string) {
    saving.value = true
    error.value = null
    try {
      await task()
    } catch (e) {
      error.value = getApiErrorMessage(e, message)
      throw e
    } finally {
      saving.value = false
    }
  }

  async function saveManual(department: number, year: number, manual: ReportManual) {
    await act(async () => {
      report.value = (await annualReportApi.saveManual(department, year, manual)).data
    }, 'Angaben konnten nicht gespeichert werden')
  }

  async function finalize(department: number, year: number) {
    await act(async () => {
      report.value = (await annualReportApi.finalize(department, year)).data
    }, 'Jahresmeldung konnte nicht festgeschrieben werden')
  }

  async function saveProfile(department: number, data: Partial<Omit<StatisticsProfile, 'id' | 'department'>>) {
    await act(async () => {
      profile.value = profile.value
        ? (await annualReportApi.updateProfile(profile.value.id, data)).data
        : (
            await annualReportApi.createProfile({
              department,
              djf_org_id: '',
              org_kind: 'JF',
              founded_on: null,
              include_status_categories: ['trial', 'active'],
              ...data
            })
          ).data
    }, 'Angaben zur Organisation konnten nicht gespeichert werden')
  }

  async function downloadXlsx(department: number, year: number) {
    await act(async () => {
      const blob = (await annualReportApi.exportXlsx(department, year)).data
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `jahresmeldung-${year}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
    }, 'Export fehlgeschlagen')
  }

  return { report, profile, loading, saving, error, load, saveManual, finalize, saveProfile, downloadXlsx }
})
