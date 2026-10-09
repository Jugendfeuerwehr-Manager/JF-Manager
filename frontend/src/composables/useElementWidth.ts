import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

/**
 * Current width of an element (falls back to the window width until it is measured
 * or where ResizeObserver is missing, e.g. in tests).
 */
export function useElementWidth(target: Ref<HTMLElement | null | undefined>) {
  const width = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
  let observer: ResizeObserver | null = null

  watch(target, (element, previous) => {
    if (typeof ResizeObserver === 'undefined') return
    observer ??= new ResizeObserver((entries) => {
      const entry = entries[entries.length - 1]
      if (entry) width.value = entry.contentRect.width
    })
    if (previous) observer.unobserve(previous)
    if (element) observer.observe(element)
  }, { immediate: true, flush: 'post' })

  onBeforeUnmount(() => observer?.disconnect())
  return width
}
