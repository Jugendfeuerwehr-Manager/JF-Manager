<template>
  <div class="canvas">
    <p v-if="!page" class="canvas__empty">Noch keine Seite. Lege oben eine Seite an und ziehe Bausteine hinein.</p>

    <template v-else>
      <section
        v-for="(section, sectionIndex) in page.sections"
        :key="section.id"
        class="canvas__section"
        :aria-label="section.title || `Abschnitt ${sectionIndex + 1}`"
      >
        <header class="canvas__section-head">
          <input
            class="canvas__section-title"
            :value="section.title"
            :aria-label="`Titel von Abschnitt ${sectionIndex + 1}`"
            placeholder="Abschnitt ohne Titel"
            :readonly="readonly"
            @change="emit('rename-section', sectionIndex, ($event.target as HTMLInputElement).value)"
          />
          <AdmButton
            v-if="!readonly"
            variant="ghost"
            icon="pi pi-trash"
            :aria-label="`Abschnitt ${section.title || sectionIndex + 1} entfernen`"
            @click="emit('remove-section', sectionIndex)"
          />
        </header>

        <ol class="canvas__list">
          <template v-for="(element, index) in section.elements" :key="element.id">
            <li
              class="bld-slot"
              :data-page="activePage"
              :data-section="sectionIndex"
              :data-index="index"
              aria-hidden="true"
            ></li>
            <li
              class="canvas__item"
              :class="{
                'canvas__item--selected': element.id === selectedId,
                'canvas__item--issue': issues.has(element.id)
              }"
            >
              <div class="canvas__row">
                <span
                  v-if="!readonly"
                  class="canvas__handle bld-draggable"
                  :data-element-id="element.id"
                  title="Ziehen zum Verschieben"
                  aria-hidden="true"
                >
                  <i class="pi pi-bars"></i>
                </span>
                <button
                  type="button"
                  class="canvas__item-main"
                  :aria-expanded="element.id === selectedId"
                  @click="emit('select', element.id === selectedId ? null : element.id)"
                >
                  <span class="canvas__label">{{ summary(element) }}</span>
                  <span class="canvas__badges">
                    <span v-if="element.required" class="canvas__badge canvas__badge--required">Pflicht</span>
                    <span v-if="element.visible_if" class="canvas__badge">bedingt</span>
                    <span v-if="element.target" class="canvas__badge" :class="{ 'canvas__badge--extra': isExtra(element) }">
                      → {{ targetLabel(element.target, references) }}
                    </span>
                    <span v-else-if="!isContent(element.type)" class="canvas__badge">{{ ELEMENT_LABELS[element.type] }}</span>
                  </span>
                </button>
              </div>
              <ul v-if="issues.get(element.id)?.length" class="canvas__issues">
                <li v-for="message in issues.get(element.id)" :key="message">
                  <i class="pi pi-exclamation-triangle" aria-hidden="true"></i> {{ message }}
                </li>
              </ul>
              <div v-if="element.id === selectedId" class="canvas__editor">
                <slot name="editor" :element="element" :first="index === 0" :last="index === section.elements.length - 1" />
              </div>
            </li>
          </template>
          <li
            class="bld-slot bld-slot--end"
            :data-page="activePage"
            :data-section="sectionIndex"
            :data-index="section.elements.length"
          >
            <span>Baustein hierher ziehen oder in der Palette antippen</span>
          </li>
        </ol>
      </section>
      <AdmButton v-if="!readonly" icon="pi pi-plus" class="canvas__add" @click="emit('add-section')">Abschnitt</AdmButton>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AdmButton from '../atoms/AdmButton.vue'
import type { BuilderReferences, FormElement, FormSchema } from '@/types/admissions'
import { ELEMENT_LABELS, isContent, targetLabel } from '@/utils/admissionSchema'

interface Props {
  schema: FormSchema
  activePage: number
  selectedId: string | null
  issues: Map<string, string[]>
  references: BuilderReferences | null
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), { readonly: false })
const emit = defineEmits<{
  (e: 'select', elementId: string | null): void
  (e: 'add-section'): void
  (e: 'rename-section', section: number, title: string): void
  (e: 'remove-section', section: number): void
}>()

const page = computed(() => props.schema.pages[props.activePage])

function isExtra(element: FormElement) {
  return (element.target ?? '').startsWith('member.extra.')
}

function summary(element: FormElement) {
  if (element.type === 'richtext') return (element.html ?? '').replace(/<[^>]+>/g, ' ').trim().slice(0, 80) || 'Textbaustein'
  if (element.type === 'divider') return 'Trennlinie'
  return element.label || ELEMENT_LABELS[element.type]
}
</script>

<style scoped>
.canvas {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.canvas__empty {
  color: var(--jf-color-text-muted);
}

.canvas__section {
  padding: var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.canvas__section-head {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
}

.canvas__section-title {
  flex: 1;
  min-width: 0;
  min-height: var(--jf-touch-target, 44px);
  padding: 0 var(--jf-space-1);
  border: 1px solid transparent;
  border-radius: var(--jf-radius-md);
  background: none;
  color: var(--jf-color-text);
  font: inherit;
  font-weight: var(--jf-weight-semibold);
  font-size: var(--jf-text-md);
}

.canvas__section-title:hover:not([readonly]),
.canvas__section-title:focus-visible {
  border-color: var(--jf-color-border);
  outline: none;
}

.canvas__list {
  list-style: none;
  margin: var(--jf-space-1) 0 0;
  padding: 0;
}

.canvas__item {
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  overflow: hidden;
}

.canvas__item--selected {
  border: 2px solid var(--jf-color-primary);
}

.canvas__item--issue:not(.canvas__item--selected) {
  border-color: var(--jf-color-warning);
}

.canvas__row {
  display: flex;
  align-items: stretch;
}

.canvas__item--selected .canvas__row {
  background: var(--jf-color-selected);
}

.canvas__handle {
  display: flex;
  align-items: center;
  padding: 0 var(--jf-space-1);
  color: var(--jf-color-text-muted);
  cursor: grab;
  touch-action: none;
}

.canvas__item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: 52px;
  padding: var(--jf-space-1) var(--jf-space-1-5) var(--jf-space-1) 0;
  border: 0;
  background: none;
  color: var(--jf-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.canvas__item-main:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: -2px;
}

.canvas__label {
  flex: 1 1 12rem;
  min-width: 0;
  font-weight: var(--jf-weight-medium);
  overflow-wrap: anywhere;
}

.canvas__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5);
}

.canvas__badge {
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  background: var(--jf-color-ground);
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text);
  white-space: nowrap;
}

.canvas__badge--required {
  background: none;
  color: var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
}

.canvas__badge--extra {
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
}

.canvas__issues {
  margin: 0;
  padding: 0 var(--jf-space-1-5) var(--jf-space-1) var(--jf-space-4, 2.5rem);
  list-style: none;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-warning);
}

.canvas__editor {
  border-top: 1px solid var(--jf-color-border);
}

.canvas__add {
  align-self: flex-start;
  border-style: dashed;
}

.bld-slot {
  height: 8px;
  margin: 2px 0;
  border-radius: var(--jf-radius-sm);
  transition: height var(--jf-duration, 120ms), background var(--jf-duration, 120ms);
}

.bld-slot--end {
  display: flex;
  align-items: center;
  justify-content: center;
  height: auto;
  min-height: var(--jf-touch-target, 44px);
  margin-top: var(--jf-space-1);
  border: 1px dashed var(--jf-color-border);
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
}

:global(.bld-dragging) .bld-slot:not(.bld-slot--end) {
  height: 18px;
  background: var(--jf-color-ground);
}

.bld-slot.bld-slot--over {
  height: 44px;
  background: var(--jf-color-selected);
  outline: 2px dashed var(--jf-color-primary);
}
</style>
