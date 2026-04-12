<template>
  <div ref="editorContainer" class="monaco-editor-container"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import loader from '@monaco-editor/loader'
import type * as Monaco from 'monaco-editor'

interface Props {
  modelValue: string
  language?: string
  theme?: 'vs' | 'vs-dark' | 'hc-black' | 'hc-light'
  readOnly?: boolean
  lineNumbers?: 'on' | 'off' | 'relative'
  wordWrap?: 'on' | 'off' | 'wordWrapColumn' | 'bounded'
  minimap?: boolean
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  language: 'html',
  theme: 'vs',
  readOnly: false,
  lineNumbers: 'on',
  wordWrap: 'on',
  minimap: true,
  height: '400px'
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()

const editorContainer = ref<HTMLDivElement>()
let editor: Monaco.editor.IStandaloneCodeEditor | null = null
let monaco: typeof Monaco | null = null

onMounted(async () => {
  if (!editorContainer.value) return

  try {
    // Load Monaco
    monaco = await loader.init()
    
    if (!monaco) return

    // Wait a tick to ensure DOM is ready
    await new Promise(resolve => setTimeout(resolve, 0))
    
    if (!editorContainer.value) return

    // Create editor
    editor = monaco.editor.create(editorContainer.value, {
      value: props.modelValue,
      language: props.language,
      theme: props.theme,
      readOnly: props.readOnly,
      lineNumbers: props.lineNumbers,
      wordWrap: props.wordWrap,
      minimap: {
        enabled: props.minimap
      },
      automaticLayout: true,
      fontSize: 14,
      tabSize: 2,
      insertSpaces: true,
      scrollBeyondLastLine: false,
      padding: { top: 10, bottom: 10 }
    })

    // Listen for content changes
    editor.onDidChangeModelContent(() => {
      const value = editor?.getValue() || ''
      emit('update:modelValue', value)
      emit('change', value)
    })
  } catch {
  }
})

onBeforeUnmount(() => {
  editor?.dispose()
})

// Watch for external value changes
watch(() => props.modelValue, (newValue) => {
  if (editor && editor.getValue() !== newValue) {
    editor.setValue(newValue)
  }
})

// Watch for language changes
watch(() => props.language, (newLanguage) => {
  if (editor && monaco) {
    const model = editor.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model, newLanguage)
    }
  }
})

// Watch for theme changes
watch(() => props.theme, (newTheme) => {
  if (monaco) {
    monaco.editor.setTheme(newTheme)
  }
})

// Watch for readonly changes
watch(() => props.readOnly, (newReadOnly) => {
  if (editor) {
    editor.updateOptions({ readOnly: newReadOnly })
  }
})
</script>

<style scoped>
.monaco-editor-container {
  width: 100%;
  height: v-bind(height);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius);
  overflow: hidden;
}
</style>
