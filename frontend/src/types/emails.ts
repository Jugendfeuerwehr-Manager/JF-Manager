/**
 * TypeScript types for the email messaging system
 */

export interface EmailMessage {
  id: number
  sender: number
  sender_name: string
  subject: string
  body_html: string
  body_text: string
  recipient_type: 'all' | 'group' | 'individual' | 'multiple'
  recipient_type_display: string
  recipient_group: number | null
  recipient_group_name: string | null
  recipient_member: number | null
  recipient_member_name: string | null
  recipient_members: number[]
  recipient_member_names: string[]
  status: 'draft' | 'sending' | 'sent' | 'failed' | 'partial'
  status_display: string
  total_recipients: number
  successful_sends: number
  failed_sends: number
  error_message: string
  created_at: string
  sent_at: string | null
}

export interface EmailMessageDetail extends EmailMessage {
  recipients: EmailRecipient[]
  attachments: EmailAttachment[]
}

export interface EmailRecipient {
  id: number
  email_address: string
  recipient_name: string
  member: number | null
  status: 'pending' | 'sent' | 'failed'
  sent_at: string | null
  error_message: string
}

export interface EmailMessageCreate {
  subject: string
  body_html: string
  body_text?: string
  layout?: string
  recipient_type: 'all' | 'group' | 'individual' | 'multiple'
  recipient_group?: number
  recipient_member?: number
  recipient_members?: number[]
  attachments?: File[]
}

export interface EmailAttachment {
  id: number
  original_filename: string
  file_size: number
  content_type: string
  created_at: string
}

export interface EmailTemplateVariable {
  variable: string
  description: string
}

export interface EmailPreviewRequest {
  subject: string
  body_html: string
  body_text?: string
  member_id: number
  layout?: string
}

export interface EmailPreviewResponse {
  rendered_html: string
  rendered_text: string
  member_name: string
  recipient_count: number
}

export interface EmailSendResponse {
  email: EmailMessageDetail
  /** Totals after an immediate send; null while the background worker sends (UX-07.2). */
  result: {
    successful: number
    failed: number
  } | null
  queued?: boolean
  /** The same request was already accepted; nothing was sent again. */
  replayed?: boolean
}

export interface EmailRecipientCountRequest {
  recipient_type: 'all' | 'group' | 'individual' | 'multiple'
  recipient_group?: number
  recipient_member?: number
  recipient_members?: number[]
}

export interface EmailRecipientCountResponse {
  count: number
  recipients: Array<{
    email: string
    name: string
    member_id: number
    member_name: string
  }>
}

/** Recipient check before sending (UX-07.1). */
export interface EmailRecipientCheckRequest extends EmailRecipientCountRequest {
  body_html?: string
  body_text?: string
}

export interface ResolvedEmailRecipient {
  email: string
  name: string
  relation: 'parent' | 'member'
  member_id: number
  member_name: string
}

export interface ExcludedEmailRecipient {
  member_id: number
  member_name: string
  /** Empty when the member has no address at all. */
  email: string
  relation: '' | 'parent' | 'member'
  reason_code: 'no_address' | 'invalid_address'
  reason: string
}

export interface EmailRecipientCheckResponse {
  /** Number of e-mails that will be sent. */
  count: number
  member_count: number
  /** The text uses member variables: every member gets its own message. */
  personalized: boolean
  merged_duplicates: number
  recipients: ResolvedEmailRecipient[]
  excluded: ExcludedEmailRecipient[]
}

export interface EmailListParams {
  limit?: number
  offset?: number
  search?: string
  status?: EmailMessage['status']
  recipient_type?: EmailMessage['recipient_type']
  recipient_group?: number
  sender?: number
  ordering?: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
