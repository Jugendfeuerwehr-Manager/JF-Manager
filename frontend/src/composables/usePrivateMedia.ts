import { ref, watch, type Ref } from 'vue'
import { mediaBlob, privateMediaPath } from '@/utils/privateMedia'

export function usePrivateMedia(source: Ref<string | null | undefined>, pdf = false) {
  const resolved = ref<string>()
  watch(source, async (value, _old, onCleanup) => {
    resolved.value = undefined
    if (!value) return
    // Local upload previews and external images never receive API credentials.
    if (!privateMediaPath(value)) {
      if (/^(https?:|blob:|data:image\/(png|jpeg|gif|webp);)/i.test(value)) resolved.value = value
      return
    }
    const controller = new AbortController()
    let objectUrl: string | undefined
    onCleanup(() => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    })
    try {
      const blob = await mediaBlob(value, controller.signal)
      const allowed = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', ...(pdf ? ['application/pdf'] : [])]
      if (controller.signal.aborted || !allowed.includes(blob.type)) return
      objectUrl = URL.createObjectURL(blob)
      resolved.value = objectUrl
    } catch {
      // Keep an empty preview when permission was revoked or the file disappeared.
    }
  }, { immediate: true })
  return resolved
}
