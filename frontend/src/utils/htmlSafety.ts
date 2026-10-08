import DOMPurify from 'dompurify'

/** HTML fragments shown in the application must never supply CSS or active content. */
export function sanitizeRichHtml(html?: string | null, isolatedEmail = false): string {
  return DOMPurify.sanitize(html ?? '', {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'a', 'ul', 'ol', 'li',
      'blockquote', 'h1', 'h2', 'h3', 'div', 'span', 'hr', 'table', 'thead',
      'tbody', 'tr', 'th', 'td',
    ],
    ALLOWED_ATTR: ['href', 'colspan', 'rowspan', ...(isolatedEmail ? ['style', 'width', 'cellpadding', 'cellspacing', 'border', 'align', 'valign'] : [])],
    ALLOW_DATA_ATTR: false,
    ALLOW_ARIA_ATTR: false,
    ALLOWED_URI_REGEXP: /^(?:https?:\/\/|mailto:)/i,
  })
}
