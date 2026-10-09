import { computed, ref, watch, type Ref } from 'vue'

/** Width limits of the planner library (px); the stylesheet also keeps it below half the planner. */
export const LIBRARY_MIN_WIDTH = 280
export const LIBRARY_MAX_WIDTH = 720
const STEP = 16
const LARGE_SCREEN = 1600
const STORAGE_PREFIX = 'jf-planner-library'

interface StoredPanel {
  width?: number
  open?: boolean
}

export function clampLibraryWidth(width: number): number {
  if (!Number.isFinite(width)) return LIBRARY_MIN_WIDTH
  return Math.round(Math.min(LIBRARY_MAX_WIDTH, Math.max(LIBRARY_MIN_WIDTH, width)))
}

/** Default width grows with the screen: 320 px on notebooks, up to 480 px on large screens. */
export function defaultLibraryWidth(viewportWidth: number): number {
  return clampLibraryWidth(Math.min(480, Math.max(320, viewportWidth * 0.22)))
}

function viewportWidth(): number {
  return typeof window === 'undefined' ? 1280 : window.innerWidth
}

function read(key: string): StoredPanel {
  try {
    const raw = localStorage.getItem(key)
    const parsed: unknown = raw ? JSON.parse(raw) : null
    return parsed && typeof parsed === 'object' ? (parsed as StoredPanel) : {}
  } catch {
    return {}
  }
}

/**
 * UX-09: size and visibility of the planner library, remembered per user in this
 * browser (only layout values, no content). Storage may be unavailable; the panel
 * then works with defaults for this visit.
 */
export function usePlannerLibraryPanel(userId: Ref<number | string | null | undefined>) {
  const storageKey = computed(() => `${STORAGE_PREFIX}:${userId.value ?? 'anonymous'}`)
  const width = ref(defaultLibraryWidth(viewportWidth()))
  const open = ref(false)

  function load() {
    const stored = read(storageKey.value)
    width.value = typeof stored.width === 'number' ? clampLibraryWidth(stored.width) : defaultLibraryWidth(viewportWidth())
    // Large screens have room for the library next to the plan; open it unless the user closed it.
    open.value = typeof stored.open === 'boolean' ? stored.open : viewportWidth() >= LARGE_SCREEN
  }

  function persist() {
    try {
      localStorage.setItem(storageKey.value, JSON.stringify({ width: width.value, open: open.value }))
    } catch {
      // Private mode or blocked storage: keep the choice for this visit only.
    }
  }

  function setWidth(next: number) {
    width.value = clampLibraryWidth(next)
    persist()
  }

  function setOpen(next: boolean) {
    open.value = next
    persist()
  }

  /** Keyboard control of the separator (panel on the right: left arrow widens). */
  function onSeparatorKey(event: KeyboardEvent): boolean {
    const step = event.shiftKey ? STEP * 4 : STEP
    const actions: Record<string, () => void> = {
      ArrowLeft: () => setWidth(width.value + step),
      ArrowRight: () => setWidth(width.value - step),
      Home: () => setWidth(LIBRARY_MIN_WIDTH),
      End: () => setWidth(LIBRARY_MAX_WIDTH),
      Enter: () => setWidth(defaultLibraryWidth(viewportWidth())),
    }
    const action = actions[event.key]
    if (!action) return false
    event.preventDefault()
    action()
    return true
  }

  /** Pointer drag on the separator; the width is stored once the drag ends. */
  function startDrag(event: PointerEvent) {
    if (event.button !== 0) return
    event.preventDefault()
    const startX = event.clientX
    const startWidth = width.value
    const handle = event.currentTarget as HTMLElement | null
    handle?.setPointerCapture?.(event.pointerId)
    const move = (e: PointerEvent) => { width.value = clampLibraryWidth(startWidth + (startX - e.clientX)) }
    const end = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', end)
      window.removeEventListener('pointercancel', end)
      persist()
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', end)
    window.addEventListener('pointercancel', end)
  }

  function reset() {
    setWidth(defaultLibraryWidth(viewportWidth()))
  }

  watch(storageKey, load, { immediate: true })

  return { width, open, setWidth, setOpen, reset, onSeparatorKey, startDrag, minWidth: LIBRARY_MIN_WIDTH, maxWidth: LIBRARY_MAX_WIDTH }
}
