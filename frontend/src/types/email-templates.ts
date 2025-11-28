/**
 * Type definitions for Email Templates
 * Supports CRUD operations and template preview functionality
 */

/**
 * Template variable definition
 * Describes available variables for template rendering
 */
export interface TemplateVariable {
  name: string
  type: string
  description: string
  properties?: string[]  // For complex types (Order, Member, etc.)
}

/**
 * Template type choice
 */
export interface TemplateType {
  value: string
  label: string
}

/**
 * Template variables metadata for a template type
 */
export interface TemplateVariables {
  variables: TemplateVariable[]
  sample_data: Record<string, any>
  warning?: string  // Warning message for legacy/unknown template types
}

/**
 * All template variables (keyed by template type)
 */
export interface AllTemplateVariables {
  [templateType: string]: TemplateVariables
}

/**
 * Email template (list view)
 */
export interface EmailTemplateList {
  id: number
  name: string
  template_type: string
  template_type_display: string
  is_active: boolean
  created_at: string
  updated_at: string
}

/**
 * Email template (detail view)
 */
export interface EmailTemplate extends EmailTemplateList {
  subject_template: string
  html_template: string
  text_template: string
  available_variables: TemplateVariable[]
}

/**
 * Email template create/update payload
 */
export interface EmailTemplateCreateUpdate {
  name?: string
  template_type: string
  subject_template: string
  html_template: string
  text_template?: string
  is_active?: boolean
}

/**
 * Template preview request
 */
export interface TemplatePreviewRequest {
  subject_template: string
  html_template: string
  text_template?: string
  sample_data?: Record<string, any>
}

/**
 * Template preview response
 */
export interface TemplatePreviewResponse {
  subject: string
  html_content: string
  text_content: string
  errors?: string[]
}

/**
 * Store state for email templates
 */
export interface EmailTemplatesState {
  templates: EmailTemplateList[]
  currentTemplate: EmailTemplate | null
  templateTypes: TemplateType[]
  allVariables: AllTemplateVariables
  loading: boolean
  saving: boolean
  previewing: boolean
  error: string | null
}
