/**
 * Block content (rich-text HTML) as pdfmake content: paragraphs, headings,
 * lists with bold/italic runs, and images. Anything else falls back to text.
 */
import type { Content } from 'pdfmake/interfaces'

/** Loads an image and returns a PNG/JPEG data URL, or null if it cannot be embedded. */
export type ImageLoader = (src: string) => Promise<string | null>

type Run = { text: string; bold?: boolean; italics?: boolean; decoration?: 'underline' }

const BLOCK_TAGS = new Set(['P', 'DIV', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'UL', 'OL', 'LI', 'BLOCKQUOTE', 'PRE', 'TABLE', 'FIGURE'])
const HEADING_SIZES: Record<string, number> = { H1: 13, H2: 12, H3: 11, H4: 10.5, H5: 10, H6: 10 }

function runs(node: Node, style: Omit<Run, 'text'> = {}): Run[] {
  if (node.nodeType === Node.TEXT_NODE) {
    const text = (node.textContent ?? '').replace(/\s+/g, ' ')
    return text ? [{ text, ...style }] : []
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return []
  const el = node as HTMLElement
  if (el.tagName === 'BR') return [{ text: '\n', ...style }]
  const next = { ...style }
  if (el.tagName === 'STRONG' || el.tagName === 'B') next.bold = true
  if (el.tagName === 'EM' || el.tagName === 'I') next.italics = true
  if (el.tagName === 'U') next.decoration = 'underline'
  return Array.from(el.childNodes).flatMap((child) => runs(child, next))
}

function trimRuns(list: Run[]): Run[] {
  const out = list.map((r) => ({ ...r }))
  if (out[0]) out[0].text = out[0].text.trimStart()
  const last = out[out.length - 1]
  if (last) last.text = last.text.trimEnd()
  return out.filter((r) => r.text)
}

export async function htmlToPdfContent(html: string, loadImage: ImageLoader, maxImageWidth = 360): Promise<Content[]> {
  const doc = new DOMParser().parseFromString(html, 'text/html')

  async function list(el: HTMLElement, ordered: boolean): Promise<Content> {
    const items: Content[] = []
    for (const li of Array.from(el.children).filter((c) => c.tagName === 'LI')) {
      const nested = await blocks(li as HTMLElement)
      items.push(nested.length === 1 ? nested[0]! : { stack: nested })
    }
    return (ordered ? { ol: items, margin: [6, 0, 0, 6] } : { ul: items, margin: [6, 0, 0, 6] }) as Content
  }

  // Children of a container: inline runs are collected into paragraphs, block elements recurse.
  async function blocks(container: HTMLElement): Promise<Content[]> {
    const out: Content[] = []
    let pending: Run[] = []
    const flush = () => {
      const text = trimRuns(pending)
      if (text.length) out.push({ text, style: 'body' } as Content)
      pending = []
    }
    for (const child of Array.from(container.childNodes)) {
      const el = child as HTMLElement
      if (child.nodeType === Node.ELEMENT_NODE && el.tagName === 'IMG') {
        flush()
        const src = (el as HTMLImageElement).getAttribute('src')
        const data = src ? await loadImage(src) : null
        if (data) out.push({ image: data, fit: [maxImageWidth, 260], margin: [0, 2, 0, 8] } as Content)
      } else if (child.nodeType === Node.ELEMENT_NODE && BLOCK_TAGS.has(el.tagName)) {
        flush()
        if (el.tagName === 'UL' || el.tagName === 'OL') out.push(await list(el, el.tagName === 'OL'))
        else if (HEADING_SIZES[el.tagName]) {
          const text = trimRuns(runs(el))
          if (text.length) out.push({ text, bold: true, fontSize: HEADING_SIZES[el.tagName], margin: [0, 4, 0, 3] } as Content)
        } else if (el.querySelector('img, ul, ol, p, div, li, h1, h2, h3, h4')) out.push(...(await blocks(el)))
        else {
          const text = trimRuns(runs(el))
          if (text.length) out.push({ text, style: 'body', ...(el.tagName === 'BLOCKQUOTE' ? { italics: true, margin: [10, 0, 0, 6] } : {}) } as Content)
        }
      } else {
        pending.push(...runs(child))
      }
    }
    flush()
    return out
  }

  return blocks(doc.body)
}
