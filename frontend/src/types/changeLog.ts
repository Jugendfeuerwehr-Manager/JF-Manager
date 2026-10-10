/** Applied changes of a member or parent record (portal requests, own changes; PORTAL-03/04). */
export interface ChangeLogEntry {
  id: number
  field: string
  label: string
  old: string
  new: string
  applied_by: string
  applied_at: string
  /** Changed by the linked account itself ("Eigenänderung", E14). */
  self_change: boolean
  via_request: boolean
}
