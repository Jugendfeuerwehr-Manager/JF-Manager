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
  recipient_type: 'all' | 'group' | 'individual'
  recipient_type_display: string
  recipient_group: number | null
  recipient_group_name: string | null
  recipient_member: number | null
  recipient_member_name: string | null
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
  recipient_type: 'all' | 'group' | 'individual'
  recipient_group?: number
  recipient_member?: number
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
}

export interface EmailPreviewResponse {
  rendered_html: string
  rendered_text: string
  member_name: string
  recipient_count: number
}

export interface EmailSendResponse {
  email: EmailMessageDetail
  result: {
    successful: number
    failed: number
  }
}

export interface EmailRecipientCountRequest {
  recipient_type: 'all' | 'group' | 'individual'
  recipient_group?: number
  recipient_member?: number
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
