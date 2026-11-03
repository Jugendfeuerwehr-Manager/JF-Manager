/**
 * TypeScript types for the admissions module (application forms, vouchers, applications).
 * The form schema mirrors backend/admissions/schema.py.
 */
import type { PaginatedResponse } from './common'

export type InputElementType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'date'
  | 'email'
  | 'phone'
  | 'select'
  | 'radio'
  | 'checkbox'
  | 'photo'
export type ContentElementType = 'heading' | 'richtext' | 'divider'
export type ElementType = InputElementType | ContentElementType | 'legal_ack' | 'consent' | 'guardians' | 'signature'

export type SignatureRole = 'applicant' | 'guardian_1' | 'guardian_2'
export type ConsentPerson = 'applicant' | 'guardians'
export type SignatureMode = 'digital' | 'print' | 'both'
export type FormAccess = 'voucher' | 'public'

export type VisibilityRule = { age_below: number } | { field: string; equals: string | boolean }

export interface ChoiceOption {
  value: string
  label: string
}

export interface GuardianFieldConfig {
  target: string
  required?: boolean
}

export interface FormElement {
  id: string
  type: ElementType
  key?: string
  label?: string
  help?: string
  required?: boolean
  target?: string | null
  options?: ChoiceOption[]
  visible_if?: VisibilityRule | null
  // richtext
  html?: string
  text_block?: number | null
  // legal / consent
  legal_kind?: string
  consent_kind?: string
  person?: ConsentPerson
  // guardians
  min?: number
  max?: number
  fields?: GuardianFieldConfig[]
  // signature
  role?: SignatureRole
  // filled in when publishing
  legal?: { title: string; body: string; version: string }
  consent?: { label: string; text: string; version: string }
}

export interface FormSection {
  id: string
  title: string
  elements: FormElement[]
}

export interface FormPage {
  id: string
  title: string
  sections: FormSection[]
}

export interface FormSchema {
  pages: FormPage[]
}

export interface SchemaIssue {
  path: string
  message: string
}

export interface AdmissionFormVersionSummary {
  id: number
  version: number
  title: string
  schema_hash: string
  change_note: string
  published_at: string
}

export interface AdmissionFormVersion extends AdmissionFormVersionSummary {
  intro: string
  signature_mode: SignatureMode
  schema: FormSchema
}

export interface AdmissionForm {
  id: number
  /** null: an organisation form serving every department */
  department: number | null
  title: string
  access: FormAccess
  public_slug: string | null
  public_departments: number[]
  intro: string
  initial_status: number | null
  signature_mode: SignatureMode
  decision_body: string
  is_active: boolean
  draft_schema: FormSchema
  draft_issues: SchemaIssue[]
  has_unpublished_changes: boolean
  current_version: AdmissionFormVersionSummary | null
  updated_at: string
}

export type AdmissionFormCreate = Pick<AdmissionForm, 'title' | 'department'> & { from_template?: boolean }
export type AdmissionFormUpdate = Partial<
  Pick<
    AdmissionForm,
    | 'title'
    | 'intro'
    | 'initial_status'
    | 'signature_mode'
    | 'decision_body'
    | 'is_active'
    | 'draft_schema'
    | 'department'
    | 'access'
    | 'public_departments'
  >
>

export interface CatalogField {
  key: string
  label: string
  input_type: InputElementType
  sensitive: boolean
}

/** An additional member field offered to the form (target ``member.extra.<key>``). */
export interface ExtraCatalogField {
  key: string
  id: number
  label: string
  input_type: InputElementType
  options: string[]
  help_text: string
  department: number | null
}

export interface BuilderReferences {
  fields: {
    member: CatalogField[]
    guardian: CatalogField[]
    extra: ExtraCatalogField[]
    gender_options: ChoiceOption[]
  }
  legal_kinds: ChoiceOption[]
  consent_kinds: { slug: string; label: string; description: string }[]
}

export interface AdmissionTextBlock {
  id: number
  department: number | null
  title: string
  body: string
  updated_at: string
}

export type AdmissionFormPage = PaginatedResponse<AdmissionForm>
export type AdmissionTextBlockPage = PaginatedResponse<AdmissionTextBlock>

/** Where an element sits in the schema. */
export interface ElementLocation {
  page: number
  section: number
  index: number
}

// ── Vouchers ────────────────────────────────────────────────────────────────

export type VoucherState = 'open' | 'used' | 'expired' | 'revoked'

export interface AdmissionVoucher {
  id: number
  form: number
  form_title: string
  department: number
  code_hint: string
  label: string
  prefill: Record<string, string>
  expires_at: string
  used_at: string | null
  revoked_at: string | null
  state: VoucherState
  application: number | null
  created_at: string
}

/** Only the create response carries the code. */
export interface CreatedVoucher extends AdmissionVoucher {
  code: string
}

export interface VoucherCreate {
  form: number
  /** required for organisation forms */
  department?: number | null
  label?: string
  vorname?: string
  nachname?: string
  valid_days?: number
}

// ── Applications, decisions, meetings ───────────────────────────────────────

export type ApplicationStatus = 'submitted' | 'approved' | 'rejected' | 'deferred' | 'withdrawn' | 'taken_over'
export type DecisionOutcome = 'approved' | 'rejected' | 'deferred'

export interface AdmissionDecision {
  id: number
  meeting: number | null
  body: string
  decided_on: string
  outcome: DecisionOutcome
  outcome_label: string
  votes_yes: number | null
  votes_no: number | null
  votes_abstain: number | null
  note: string
  recorded_by_name: string
  recorded_at: string
}

export interface ApplicationListItem {
  id: number
  department: number
  applicant_name: string
  status: ApplicationStatus
  status_label: string
  form_title: string
  form_version_number: number
  submitted_at: string
  member: number | null
}

export interface ApplicationFileRef {
  kind: 'photo' | 'signature'
  sha256: string
  url: string
}

export interface ApplicationDetail extends ApplicationListItem {
  answers: Record<string, unknown>
  schema: FormSchema
  signature_mode: SignatureMode
  decision_body: string
  decisions: AdmissionDecision[]
  files: Record<string, ApplicationFileRef>
  taken_over_at: string | null
}

export interface SealCheck {
  valid: boolean
  signature: boolean
  content: boolean
  chain: boolean
  current_key: boolean
  content_checked: boolean
  kind: 'submission' | 'decision' | 'export' | 'annual_report'
  sealed_at: string
  public_id: string
  seal_hash: string
}

export interface ApplicationVerification {
  valid: boolean
  seals: SealCheck[]
}

export interface ApplicationExport extends ApplicationDetail {
  seals: SealCheck[]
  export_seal: { public_id: string; seal_hash: string; sealed_at: string }
}

export interface DecisionInput {
  outcome: DecisionOutcome
  decided_on?: string
  meeting?: number | null
  votes_yes?: number | null
  votes_no?: number | null
  votes_abstain?: number | null
  note?: string
}

export interface TakeOverInput {
  joined?: string
  parent_links?: Record<string, number | null>
  invite_parents?: boolean
}

export interface ParentSuggestion {
  id: number
  name: string
  email: string
}

export interface CommitteeMeeting {
  id: number
  department: number
  body: string
  date: string
  protocol_ref: string
  note: string
  decision_count: number
  created_at: string
}

// ── Public form ─────────────────────────────────────────────────────────────

export interface PublicDepartment {
  id: number
  name: string
}

export interface PublicAdmissionForm {
  department: string
  /** public link only: departments the applicant may choose */
  departments?: PublicDepartment[]
  title: string
  intro: string
  signature_mode: SignatureMode
  decision_body: string
  version: number
  schema: FormSchema
  prefill: Record<string, string>
  expires_at: string | null
}

export interface PublicSubmitResult {
  applicant_name: string
  submitted_at: string
  seal: { public_id: string; seal_hash: string }
}

export interface PublicSealCheck {
  valid: boolean
  kind: string
  sealed_at: string
  content_checked: boolean
  signature: boolean
  chain: boolean
}
