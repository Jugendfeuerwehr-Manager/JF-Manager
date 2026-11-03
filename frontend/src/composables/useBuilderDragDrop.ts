/**
 * Drag & drop for the form builder (interact.js, works with mouse, pen and touch).
 *
 * Draggables carry ``data-type`` (a new element from the palette) or ``data-element-id`` (an
 * existing element); drop slots carry ``data-page``, ``data-section`` and ``data-index``.
 * A floating copy follows the pointer so palette and canvas keep their layout.
 */
import { onBeforeUnmount, onMounted } from 'vue'
import interact from 'interactjs'
import type { ElementLocation, ElementType } from '@/types/admissions'

export type DragSource = { kind: 'new'; type: ElementType } | { kind: 'move'; elementId: string }

const DRAGGABLE = '.bld-draggable'
const SLOT = '.bld-slot'

function sourceOf(element: HTMLElement): DragSource | null {
  if (element.dataset.type) return { kind: 'new', type: element.dataset.type as ElementType }
  if (element.dataset.elementId) return { kind: 'move', elementId: element.dataset.elementId }
  return null
}

function locationOf(element: HTMLElement): ElementLocation | null {
  const { page, section, index } = element.dataset
  if (page === undefined || section === undefined || index === undefined) return null
  return { page: Number(page), section: Number(section), index: Number(index) }
}

function swallowNextClick() {
  const stop = (event: Event) => {
    event.stopPropagation()
    event.preventDefault()
  }
  window.addEventListener('click', stop, { capture: true, once: true })
  // If no click follows (touch), drop the guard so the next real click works.
  setTimeout(() => window.removeEventListener('click', stop, { capture: true }), 200)
}

export function useBuilderDragDrop(onDrop: (source: DragSource, target: ElementLocation) => void, enabled: () => boolean) {
  let ghost: HTMLElement | null = null

  function startGhost(element: HTMLElement, x: number, y: number) {
    const tile = element.closest('.canvas__item, .palette__tile') as HTMLElement | null
    ghost = (tile ?? element).cloneNode(true) as HTMLElement
    const rect = (tile ?? element).getBoundingClientRect()
    Object.assign(ghost.style, {
      position: 'fixed',
      left: '0',
      top: '0',
      width: `${Math.min(rect.width, 420)}px`,
      pointerEvents: 'none',
      opacity: '0.9',
      zIndex: '1000',
      boxShadow: 'var(--jf-shadow-lg)',
      transform: `translate(${x + 8}px, ${y + 8}px)`
    })
    document.body.appendChild(ghost)
    document.body.classList.add('bld-dragging')
  }

  function moveGhost(x: number, y: number) {
    if (ghost) ghost.style.transform = `translate(${x + 8}px, ${y + 8}px)`
  }

  function endGhost() {
    ghost?.remove()
    ghost = null
    document.body.classList.remove('bld-dragging')
  }

  onMounted(() => {
    interact(DRAGGABLE).draggable({
      // A short hold on touch devices keeps scrolling usable.
      hold: 0,
      listeners: {
        start(event) {
          if (!enabled()) return event.interaction.stop()
          startGhost(event.target as HTMLElement, event.client.x, event.client.y)
        },
        move(event) {
          moveGhost(event.client.x, event.client.y)
        },
        end() {
          endGhost()
          swallowNextClick()
        }
      }
    })

    interact(SLOT).dropzone({
      accept: DRAGGABLE,
      overlap: 'pointer',
      ondragenter(event) {
        ;(event.target as HTMLElement).classList.add('bld-slot--over')
      },
      ondragleave(event) {
        ;(event.target as HTMLElement).classList.remove('bld-slot--over')
      },
      ondrop(event) {
        const slot = event.target as HTMLElement
        slot.classList.remove('bld-slot--over')
        const source = sourceOf(event.relatedTarget as HTMLElement)
        const target = locationOf(slot)
        if (!source || !target) return
        onDrop(source, target)
      }
    })
  })

  onBeforeUnmount(() => {
    endGhost()
    interact(DRAGGABLE).unset()
    interact(SLOT).unset()
  })
}
