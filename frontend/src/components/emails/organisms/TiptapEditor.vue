<template>
  <div class="tiptap-editor" :class="{ 'is-mobile': isMobile }">
    <!-- Toolbar -->
    <div v-if="editor" class="editor-toolbar">
      <div class="toolbar-group">
        <Button
          label="B"
          :severity="editor.isActive('bold') ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().toggleBold().run()"
          :title="'Fett'"
          size="small"
          class="font-bold"
        />
        <Button
          label="I"
          :severity="editor.isActive('italic') ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().toggleItalic().run()"
          :title="'Kursiv'"
          size="small"
          class="italic"
        />
        <Button
          label="U"
          :severity="editor.isActive('underline') ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().toggleUnderline().run()"
          :title="'Unterstrichen'"
          size="small"
          class="underline"
        />
      </div>

      <div class="toolbar-group">
        <Button
          icon="pi pi-align-left"
          :severity="editor.isActive({ textAlign: 'left' }) ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().setTextAlign('left').run()"
          :title="'Linksbündig'"
          size="small"
        />
        <Button
          icon="pi pi-align-center"
          :severity="editor.isActive({ textAlign: 'center' }) ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().setTextAlign('center').run()"
          :title="'Zentriert'"
          size="small"
        />
        <Button
          icon="pi pi-align-right"
          :severity="editor.isActive({ textAlign: 'right' }) ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().setTextAlign('right').run()"
          :title="'Rechtsbündig'"
          size="small"
        />
      </div>

      <div class="toolbar-group">
        <Button
          icon="pi pi-list"
          :severity="editor.isActive('bulletList') ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().toggleBulletList().run()"
          :title="'Aufzählung'"
          size="small"
        />
        <Button
          icon="pi pi-list"
          :severity="editor.isActive('orderedList') ? 'primary' : 'secondary'"
          text
          @click="editor.chain().focus().toggleOrderedList().run()"
          :title="'Nummerierung'"
          size="small"
        />
      </div>

      <div class="toolbar-group">
        <Dropdown
          v-model="selectedHeading"
          :options="headingOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Format"
          @change="setHeading"
          class="heading-dropdown"
        />
      </div>
    </div>

    <!-- Editor Content -->
    <EditorContent :editor="editor" class="editor-content" />

    <!-- Signature Preview -->
    <div v-if="signature && includeSignature" class="signature-section">
      <div class="signature-divider">
        <span>Signatur</span>
      </div>
      <div class="signature-content" v-html="signature"></div>
    </div>

    <!-- Template Variables -->
    <div v-if="showVariables && templateVariables.length > 0" class="template-variables">
      <div class="variables-header">
        <span class="variables-title">
          <i class="pi pi-code"></i>
          Variablen
        </span>
      </div>
      <div class="variables-list">
        <Button
          v-for="variable in templateVariables"
          :key="variable.variable"
          :label="variable.variable"
          text
          size="small"
          @click="insertVariable(variable.variable)"
          :title="variable.description"
          class="variable-button"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import type { EmailTemplateVariable } from '@/types/emails'

interface Props {
  modelValue: string
  placeholder?: string
  templateVariables?: EmailTemplateVariable[]
  showVariables?: boolean
  signature?: string
  includeSignature?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'E-Mail-Text eingeben...',
  templateVariables: () => [],
  showVariables: true,
  signature: '',
  includeSignature: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const isMobile = ref(window.innerWidth < 768)
const selectedHeading = ref('paragraph')

const headingOptions = [
  { label: 'Normal', value: 'paragraph' },
  { label: 'Überschrift 1', value: 'h1' },
  { label: 'Überschrift 2', value: 'h2' },
  { label: 'Überschrift 3', value: 'h3' }
]

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit,
    Underline,
    TextAlign.configure({
      types: ['heading', 'paragraph']
    }),
    Link.configure({
      openOnClick: false
    }),
    Placeholder.configure({
      placeholder: props.placeholder
    })
  ],
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  },
  editorProps: {
    attributes: {
      class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl focus:outline-none'
    }
  }
})

watch(() => props.modelValue, (value) => {
  const isSame = editor.value?.getHTML() === value
  if (!isSame && editor.value) {
    editor.value.commands.setContent(value)
  }
})

const setHeading = () => {
  if (!editor.value) return

  if (selectedHeading.value === 'paragraph') {
    editor.value.chain().focus().setParagraph().run()
  } else {
    const level = parseInt(selectedHeading.value.replace('h', '')) as 1 | 2 | 3
    editor.value.chain().focus().toggleHeading({ level }).run()
  }
}

const insertVariable = (variable: string) => {
  if (!editor.value) return
  editor.value.chain().focus().insertContent(variable).run()
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  editor.value?.destroy()
})
</script>

<style scoped>
.tiptap-editor {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-50);
}

.is-mobile .editor-toolbar {
  padding: 0.5rem;
  gap: 0.25rem;
}

.toolbar-group {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.toolbar-group:not(:last-child) {
  padding-right: 0.5rem;
  border-right: 1px solid var(--surface-border);
}

.is-mobile .toolbar-group:not(:last-child) {
  padding-right: 0.25rem;
}

.heading-dropdown {
  min-width: 150px;
}

.is-mobile .heading-dropdown {
  min-width: 120px;
}

.editor-content {
  min-height: 300px;
  padding: 1rem;
}

.is-mobile .editor-content {
  min-height: 200px;
  padding: 0.75rem;
}

.editor-content :deep(.ProseMirror) {
  outline: none;
  min-height: 250px;
}

.is-mobile .editor-content :deep(.ProseMirror) {
  min-height: 150px;
}

.editor-content :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--text-color-secondary);
  pointer-events: none;
  height: 0;
}

.template-variables {
  border-top: 1px solid var(--surface-border);
  padding: 0.75rem;
  background: var(--surface-50);
}

.variables-header {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
}

.variables-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.variables-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.variable-button {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.variable-button:hover {
  background: var(--surface-hover);
}

.signature-section {
  border-top: 1px solid var(--surface-border);
  padding: 1rem;
  background: var(--surface-100);
}

.signature-divider {
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  font-weight: 500;
}

.signature-divider::before,
.signature-divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px dashed var(--surface-border);
}

.signature-divider span {
  padding: 0 0.75rem;
}

.signature-content {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  pointer-events: none;
  user-select: none;
  opacity: 0.85;
}

.signature-content :deep(*) {
  color: inherit !important;
}

.signature-content :deep(strong) {
  font-weight: 600;
}

.signature-content :deep(em) {
  font-style: italic;
}

.signature-content :deep(u) {
  text-decoration: underline;
}

.signature-content :deep(h1),
.signature-content :deep(h2),
.signature-content :deep(h3) {
  font-weight: 600;
  margin-top: 0.5rem;
  margin-bottom: 0.25rem;
}

.signature-content :deep(ul),
.signature-content :deep(ol) {
  margin-left: 1.5rem;
  margin-top: 0.25rem;
  margin-bottom: 0.25rem;
}

.signature-content :deep(p) {
  margin-bottom: 0.25rem;
}
</style>
