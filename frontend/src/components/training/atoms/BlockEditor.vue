<template>
  <div class="block-editor" @drop.prevent="onDrop" @dragover.prevent @paste="onPaste">
    <!-- Toolbar -->
    <div v-if="editor" class="editor-toolbar">
      <div class="toolbar-group">
        <Button
          label="B"
          :severity="editor.isActive('bold') ? 'primary' : 'secondary'"
          text size="small" class="font-bold"
          @click="editor.chain().focus().toggleBold().run()"
        />
        <Button
          label="I"
          :severity="editor.isActive('italic') ? 'primary' : 'secondary'"
          text size="small" class="italic"
          @click="editor.chain().focus().toggleItalic().run()"
        />
        <Button
          label="U"
          :severity="editor.isActive('underline') ? 'primary' : 'secondary'"
          text size="small" class="underline"
          @click="editor.chain().focus().toggleUnderline().run()"
        />
      </div>

      <div class="toolbar-group">
        <Button
          icon="pi pi-align-left"
          :severity="editor.isActive({ textAlign: 'left' }) ? 'primary' : 'secondary'"
          text size="small"
          @click="editor.chain().focus().setTextAlign('left').run()"
        />
        <Button
          icon="pi pi-align-center"
          :severity="editor.isActive({ textAlign: 'center' }) ? 'primary' : 'secondary'"
          text size="small"
          @click="editor.chain().focus().setTextAlign('center').run()"
        />
        <Button
          icon="pi pi-align-right"
          :severity="editor.isActive({ textAlign: 'right' }) ? 'primary' : 'secondary'"
          text size="small"
          @click="editor.chain().focus().setTextAlign('right').run()"
        />
      </div>

      <div class="toolbar-group">
        <Button
          icon="pi pi-list"
          :severity="editor.isActive('bulletList') ? 'primary' : 'secondary'"
          text size="small" title="Aufzählung"
          @click="editor.chain().focus().toggleBulletList().run()"
        />
        <Button
          icon="pi pi-sort-amount-down"
          :severity="editor.isActive('orderedList') ? 'primary' : 'secondary'"
          text size="small" title="Nummerierte Liste"
          @click="editor.chain().focus().toggleOrderedList().run()"
        />
      </div>

      <div class="toolbar-group">
        <Select
          v-model="selectedHeading"
          :options="headingOptions"
          option-label="label"
          option-value="value"
          @change="setHeading"
          class="heading-select"
        />
      </div>

      <div class="toolbar-group">
        <!-- Image upload button -->
        <Button
          icon="pi pi-image"
          severity="secondary"
          text size="small"
          title="Bild einfügen"
          :loading="uploading"
          @click="triggerImageUpload"
        />
        <input
          ref="imageInput"
          type="file"
          accept="image/*"
          class="hidden"
          @change="onImageFileSelected"
        />
      </div>
    </div>

    <!-- Image inline toolbar (appears when an image is selected) -->
    <div v-if="editor && editor.isActive('image')" class="image-toolbar">
      <span class="text-sm text-color-secondary mr-2">Bild:</span>
      <Button icon="pi pi-align-left" text size="small" title="Links"
        @click="editor.chain().focus().setImage({ ...getSelectedImageAttrs(), style: 'float:left; margin-right:1em' }).run()" />
      <Button icon="pi pi-align-center" text size="small" title="Zentriert"
        @click="editor.chain().focus().setImage({ ...getSelectedImageAttrs(), style: 'display:block;margin:auto' }).run()" />
      <Button icon="pi pi-align-right" text size="small" title="Rechts"
        @click="editor.chain().focus().setImage({ ...getSelectedImageAttrs(), style: 'float:right; margin-left:1em' }).run()" />
      <Button icon="pi pi-trash" severity="danger" text size="small" title="Bild löschen"
        @click="editor.chain().focus().deleteSelection().run()" />
    </div>

    <!-- Drop zone overlay -->
    <div v-if="draggingOver" class="drop-overlay">
      <div class="drop-message">
        <i class="pi pi-image text-4xl mb-2"></i>
        <span>Bild hier ablegen</span>
      </div>
    </div>

    <EditorContent :editor="editor" class="editor-content" />

    <!-- Upload progress -->
    <div v-if="uploading" class="upload-progress">
      <i class="pi pi-spin pi-spinner mr-2"></i>
      <span>Bild wird hochgeladen…</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import Image from '@tiptap/extension-image'
import Dropcursor from '@tiptap/extension-dropcursor'
import Gapcursor from '@tiptap/extension-gapcursor'
import Button from 'primevue/button'
import Select from 'primevue/select'
import { useBlockMediaUpload } from '@/composables/useBlockMediaUpload'

interface Props {
  modelValue: string
  placeholder?: string
  blockType?: 'library' | 'training'
  blockId?: number | null
  minHeight?: string
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Inhalt eingeben…',
  blockType: 'library',
  blockId: null,
  minHeight: '200px',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const imageInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const draggingOver = ref(false)
const selectedHeading = ref('paragraph')

const blockIdRef = computed(() => props.blockId ?? null)
const { handleEditorDrop, handleEditorPaste, uploadImage } =
  useBlockMediaUpload(props.blockType, blockIdRef)

const headingOptions = [
  { label: 'Normal', value: 'paragraph' },
  { label: 'Überschrift 1', value: 'h1' },
  { label: 'Überschrift 2', value: 'h2' },
  { label: 'Überschrift 3', value: 'h3' },
]

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit,
    Underline,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Link.configure({ openOnClick: false }),
    Placeholder.configure({ placeholder: props.placeholder }),
    Image.configure({ inline: true, allowBase64: false }),
    Dropcursor,
    Gapcursor,
  ],
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  },
  editorProps: {
    attributes: {
      class: 'prose focus:outline-none',
    },
  },
})

watch(
  () => props.modelValue,
  (value) => {
    if (editor.value && editor.value.getHTML() !== value) {
      editor.value.commands.setContent(value)
    }
  }
)

function setHeading() {
  if (!editor.value) return
  if (selectedHeading.value === 'paragraph') {
    editor.value.chain().focus().setParagraph().run()
  } else {
    const level = parseInt(selectedHeading.value.replace('h', '')) as 1 | 2 | 3
    editor.value.chain().focus().toggleHeading({ level }).run()
  }
}

function getSelectedImageAttrs() {
  if (!editor.value) return {}
  const { attrs } = editor.value.getAttributes('image')
  return attrs ?? {}
}

function triggerImageUpload() {
  imageInput.value?.click()
}

async function onImageFileSelected(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file || !editor.value) return
  await embedImageFile(file)
  // Reset input to allow re-selecting same file
  if (imageInput.value) imageInput.value.value = ''
}

async function embedImageFile(file: File) {
  if (!editor.value) return
  uploading.value = true
  try {
    const media = await uploadImage(file)
    editor.value.chain().focus().setImage({ src: media.url, alt: media.original_filename }).run()
  } finally {
    uploading.value = false
  }
}

async function onDrop(event: DragEvent) {
  if (!editor.value) return
  draggingOver.value = false

  // Handle img HTML dragged from AssetPanel (sets text/plain = '<img src=... />')
  const htmlContent = event.dataTransfer?.getData('text/plain')
  if (htmlContent?.trimStart().startsWith('<img')) {
    event.preventDefault()
    editor.value.chain().focus().insertContent(htmlContent).run()
    return
  }

  uploading.value = true
  try {
    await handleEditorDrop(editor.value, event)
  } finally {
    uploading.value = false
  }
}

async function onPaste(event: ClipboardEvent) {
  if (!editor.value) return
  uploading.value = true
  try {
    await handleEditorPaste(editor.value, event)
  } finally {
    uploading.value = false
  }
}

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style scoped>
.block-editor {
  position: relative;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0.5rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-50);
  align-items: center;
}

.toolbar-group {
  display: flex;
  gap: 0.125rem;
  align-items: center;
  padding-right: 0.5rem;
  border-right: 1px solid var(--surface-border);
}
.toolbar-group:last-child {
  border-right: none;
}

.heading-select {
  width: 9rem;
  font-size: 0.875rem;
}

.image-toolbar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: var(--primary-50, #eff6ff);
  border-bottom: 1px solid var(--surface-border);
}

.editor-content {
  padding: 0.75rem 1rem;
  min-height: v-bind(minHeight);
  cursor: text;
}

.editor-content :deep(.ProseMirror) {
  outline: none;
  min-height: inherit;
}

.editor-content :deep(img) {
  max-width: 100%;
  cursor: pointer;
  border-radius: 4px;
}
.editor-content :deep(img.ProseMirror-selectednode) {
  outline: 3px solid var(--primary-color);
}

.drop-overlay {
  position: absolute;
  inset: 0;
  background: rgba(99, 102, 241, 0.1);
  border: 2px dashed var(--primary-color);
  border-radius: var(--border-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
}
.drop-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: var(--primary-color);
  font-weight: 600;
}

.upload-progress {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  border-top: 1px solid var(--surface-border);
}

.hidden {
  display: none;
}
</style>
