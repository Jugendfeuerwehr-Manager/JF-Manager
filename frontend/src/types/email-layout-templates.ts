export interface EmailLayoutTemplate {
  layout_type: 'general' | 'important' | 'events'
  label: string
  html_content: string
  is_custom: boolean
  updated_at: string | null
}

export interface EmailLayoutTemplateUpdate {
  html_content: string
}
