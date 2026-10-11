export type ListPreferenceView = 'members'

/** Filters, sorting and page size only; the server rejects search texts. */
export interface ListPreferenceData {
  status?: number | null
  group?: number | null
  gender?: string
  rows?: number
  sortField?: string
  sortOrder?: 1 | -1
}

export interface ListPreference {
  view: ListPreferenceView
  department: number | null
  data: ListPreferenceData
}
