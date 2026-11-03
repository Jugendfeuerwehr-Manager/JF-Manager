import { defineStore } from 'pinia'
import { ref } from 'vue'
import { privacyApi } from '@/api/privacy'
import type {
  ConsentCreate,
  ConsentKind,
  ConsentKindInput,
  ConsentRecord,
  ConsentSubject,
  LegalPage,
  LegalPageDraft,
  LegalPageKind,
  LegalPageVersion,
  PublicLegalPage,
} from '@/types/privacy'
import { getApiErrorMessage } from '@/utils/apiError'

export const usePrivacyStore = defineStore('privacy', () => {
  // Legal text editor (settings)
  const legalPages = ref<LegalPage[]>([])
  const versions = ref<Record<string, LegalPageVersion[]>>({})
  const legalLoading = ref(false)
  const legalSaving = ref(false)
  const legalError = ref<string | null>(null)

  // Public legal page
  const publicPage = ref<PublicLegalPage | null>(null)
  const publicLoading = ref(false)
  const publicError = ref<string | null>(null)

  // Consents of the person currently shown
  const consents = ref<ConsentRecord[]>([])
  const consentsLoading = ref(false)
  const consentsSaving = ref(false)
  const consentsError = ref<string | null>(null)

  // Kinds of consent (labels, choices; editable in the privacy settings)
  const consentKinds = ref<ConsentKind[]>([])
  const kindsLoading = ref(false)
  const kindsSaving = ref(false)
  const kindsError = ref<string | null>(null)

  async function fetchConsentKinds() {
    kindsLoading.value = true
    kindsError.value = null
    try {
      consentKinds.value = (await privacyApi.consentKinds()).data
    } catch (e) {
      kindsError.value = getApiErrorMessage(e, 'Einwilligungsarten konnten nicht geladen werden')
    } finally {
      kindsLoading.value = false
    }
  }

  async function saveConsentKind(data: ConsentKindInput, id?: number) {
    kindsSaving.value = true
    kindsError.value = null
    try {
      const kind = (id ? await privacyApi.updateConsentKind(id, data) : await privacyApi.createConsentKind(data)).data
      consentKinds.value = id
        ? consentKinds.value.map(item => (item.id === id ? kind : item))
        : [...consentKinds.value, kind]
      return true
    } catch (e) {
      kindsError.value = getApiErrorMessage(e, 'Einwilligungsart konnte nicht gespeichert werden')
      return false
    } finally {
      kindsSaving.value = false
    }
  }

  async function deleteConsentKind(id: number) {
    kindsError.value = null
    try {
      await privacyApi.deleteConsentKind(id)
      consentKinds.value = consentKinds.value.filter(item => item.id !== id)
      return true
    } catch (e) {
      kindsError.value = getApiErrorMessage(e, 'Einwilligungsart konnte nicht gelöscht werden')
      return false
    }
  }

  function replacePage(page: LegalPage) {
    legalPages.value = legalPages.value.map(item => (item.kind === page.kind ? page : item))
  }

  async function fetchLegalPages() {
    legalLoading.value = true
    legalError.value = null
    try {
      legalPages.value = (await privacyApi.legalPages()).data
    } catch (e) {
      legalError.value = getApiErrorMessage(e, 'Rechtstexte konnten nicht geladen werden')
    } finally {
      legalLoading.value = false
    }
  }

  async function saveDraft(kind: LegalPageKind, data: LegalPageDraft) {
    legalSaving.value = true
    legalError.value = null
    try {
      replacePage((await privacyApi.saveDraft(kind, data)).data)
      return true
    } catch (e) {
      legalError.value = getApiErrorMessage(e, 'Entwurf konnte nicht gespeichert werden')
      return false
    } finally {
      legalSaving.value = false
    }
  }

  async function publish(kind: LegalPageKind, changeNote: string) {
    legalSaving.value = true
    legalError.value = null
    try {
      replacePage((await privacyApi.publish(kind, changeNote)).data)
      await fetchVersions(kind)
      return true
    } catch (e) {
      legalError.value = getApiErrorMessage(e, 'Veröffentlichen fehlgeschlagen')
      return false
    } finally {
      legalSaving.value = false
    }
  }

  async function fetchVersions(kind: LegalPageKind) {
    try {
      versions.value = { ...versions.value, [kind]: (await privacyApi.versions(kind)).data }
    } catch (e) {
      legalError.value = getApiErrorMessage(e, 'Versionen konnten nicht geladen werden')
    }
  }

  async function fetchPublicPage(kind: LegalPageKind) {
    publicLoading.value = true
    publicError.value = null
    publicPage.value = null
    try {
      publicPage.value = (await privacyApi.publicPage(kind)).data
    } catch (e) {
      publicError.value = getApiErrorMessage(e, 'Dieser Text ist noch nicht veröffentlicht.')
    } finally {
      publicLoading.value = false
    }
  }

  async function fetchConsents(subject: ConsentSubject) {
    consentsLoading.value = true
    consentsError.value = null
    try {
      consents.value = (await privacyApi.consents(subject)).data
    } catch (e) {
      consents.value = []
      consentsError.value = getApiErrorMessage(e, 'Einwilligungen konnten nicht geladen werden')
    } finally {
      consentsLoading.value = false
    }
  }

  async function recordConsent(subject: ConsentSubject, data: ConsentCreate) {
    consentsSaving.value = true
    consentsError.value = null
    try {
      const record = (await privacyApi.recordConsent(subject, data)).data
      consents.value = [record, ...consents.value]
      return true
    } catch (e) {
      consentsError.value = getApiErrorMessage(e, 'Einwilligung konnte nicht gespeichert werden')
      return false
    } finally {
      consentsSaving.value = false
    }
  }

  // Art. 15 DSGVO: ZIP with all data of one person (step-up is handled by the API client).
  const exporting = ref(false)

  async function downloadSubjectAccess(subject: ConsentSubject) {
    exporting.value = true
    consentsError.value = null
    try {
      const response = await privacyApi.subjectAccess(subject)
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `datenauskunft-${subject.field}-${subject.id}.zip`
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      return true
    } catch (e) {
      consentsError.value = getApiErrorMessage(e, 'Datenauskunft konnte nicht erstellt werden')
      return false
    } finally {
      exporting.value = false
    }
  }

  return {
    consentKinds,
    kindsLoading,
    kindsSaving,
    kindsError,
    fetchConsentKinds,
    saveConsentKind,
    deleteConsentKind,
    exporting,
    downloadSubjectAccess,
    legalPages,
    versions,
    legalLoading,
    legalSaving,
    legalError,
    publicPage,
    publicLoading,
    publicError,
    consents,
    consentsLoading,
    consentsSaving,
    consentsError,
    fetchLegalPages,
    saveDraft,
    publish,
    fetchVersions,
    fetchPublicPage,
    fetchConsents,
    recordConsent,
  }
})
