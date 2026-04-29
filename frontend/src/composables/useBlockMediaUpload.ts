import type { Ref } from 'vue'
import type { Editor } from '@tiptap/core'
import { libraryApi, trainingBlocksApi } from '@/api/training'
import type { TrainingMedia } from '@/types/training'

/**
 * Reusable composable for uploading images into block rich-text editors.
 * Shared by LibraryBlockForm and BlockEditDialog.
 */
export function useBlockMediaUpload(
  blockType: 'library' | 'training',
  blockId: Ref<number | null>
) {
  const api = blockType === 'library' ? libraryApi : trainingBlocksApi

  async function uploadImage(file: File): Promise<TrainingMedia> {
    if (!blockId.value) throw new Error('Block ID not set')
    const response = await api.uploadImage(blockId.value, file)
    return response.data
  }

  /**
   * Handle a DragEvent on the editor container.
   * If the dragged item is an image file, upload it and embed via Tiptap.
   * Returns true if the event was handled (so the caller can preventDefault).
   */
  async function handleEditorDrop(
    editor: Editor,
    event: DragEvent
  ): Promise<boolean> {
    const files = event.dataTransfer?.files
    if (!files || files.length === 0) return false

    const imageFiles = Array.from(files).filter((f) => f.type.startsWith('image/'))
    if (imageFiles.length === 0) return false

    event.preventDefault()

    for (const file of imageFiles) {
      try {
        const media = await uploadImage(file)
        // Get drop position
        const coords = { left: event.clientX, top: event.clientY }
        const pos = editor.view.posAtCoords(coords)?.pos
        if (pos !== undefined) {
          editor.chain().focus().insertContentAt(pos, {
            type: 'image',
            attrs: { src: media.url, alt: media.original_filename },
          }).run()
        } else {
          editor.chain().focus().setImage({ src: media.url, alt: media.original_filename }).run()
        }
      } catch {
        // silently ignore failed uploads to not block other files
      }
    }
    return true
  }

  /**
   * Handles paste events with image data (e.g. pasting screenshots).
   */
  async function handleEditorPaste(
    editor: Editor,
    event: ClipboardEvent
  ): Promise<boolean> {
    const items = event.clipboardData?.items
    if (!items) return false

    const imageItems = Array.from(items).filter((i) => i.type.startsWith('image/'))
    if (imageItems.length === 0) return false

    event.preventDefault()

    for (const item of imageItems) {
      const file = item.getAsFile()
      if (!file) continue
      try {
        const media = await uploadImage(file)
        editor.chain().focus().setImage({ src: media.url, alt: 'Eingefügtes Bild' }).run()
      } catch {
        // silently ignore
      }
    }
    return true
  }

  return { uploadImage, handleEditorDrop, handleEditorPaste }
}
