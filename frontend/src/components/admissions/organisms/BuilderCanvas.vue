<template>
  <div class="canvas">
    <nav class="canvas__pages" aria-label="Seiten des Formulars">
      <button
        v-for="(page, pageIndex) in schema.pages"
        :key="page.id"
        type="button"
        class="canvas__page-tab"
        :class="{ 'canvas__page-tab--active': pageIndex === activePage }"
        :aria-current="pageIndex === activePage ? 'page' : undefined"
        @click="emit('select-page', pageIndex)"
      >
        {{ pageIndex + 1 }}. {{ page.title }}
      </button>
      <AdmButton variant="ghost" icon="pi pi-plus" @click="emit('add-page')">Seite</AdmButton>
    </nav>

    <p v-if="!page" class="canvas__empty">Noch keine Seite. Lege eine Seite an und ziehe Elemente hinein.</p>

    <template v-else>
      <section
        v-for="(section, sectionIndex) in page.sections"
        :key="section.id"
        class="canvas__section"
        :class="{ 'canvas__section--selected': isSectionSelected(sectionIndex) }"
      >
        <header class="canvas__section-head">
          <button type="button" class="canvas__section-title" @click="emit('select-section', sectionIndex)">
            {{ section.title || 'Abschnitt ohne Titel' }}
          </button>
          <span class="canvas__count">{{ section.elements.length }} Elemente</span>
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
              <span
                v-if="!readonly"
                class="canvas__handle bld-draggable"
                :data-element-id="element.id"
                title="Ziehen zum Verschieben"
                aria-hidden="true"
              >
                <i class="pi pi-bars"></i>
              </span>
              <button type="button" class="canvas__item-main" @click="emit('select', element.id)">
                <span class="canvas__type"><i :class="iconFor(element.type)" aria-hidden="true"></i> {{ ELEMENT_LABELS[element.type] }}</span>
                <span class="canvas__label">{{ summary(element) }}</span>
                <span class="canvas__badges">
                  <span v-if="element.required" class="canvas__badge">Pflicht</span>
                  <span v-if="element.target" class="canvas__badge canvas__badge--target">→ {{ element.target }}</span>
                  <span v-if="element.visible_if" class="canvas__badge">bedingt</span>
                </span>
                <span v-for="message in issues.get(element.id) ?? []" :key="message" class="canvas__issue">
                  <i class="pi pi-exclamation-triangle" aria-hidden="true"></i> {{ message }}
                </span>
              </button>
              <span v-if="!readonly" class="canvas__actions">
                <AdmButton
                  variant="ghost"
                  icon="pi pi-arrow-up"
                  :aria-label="`${summary(element)} nach oben`"
                  :disabled="index === 0"
                  @click="emit('move', element.id, -1)"
                />
                <AdmButton
                  variant="ghost"
                  icon="pi pi-arrow-down"
                  :aria-label="`${summary(element)} nach unten`"
                  :disabled="index === section.elements.length - 1"
                  @click="emit('move', element.id, 1)"
                />
              </span>
            </li>
          </template>
          <li
            class="bld-slot bld-slot--end"
            :data-page="activePage"
            :data-section="sectionIndex"
            :data-index="section.elements.length"
          >
            <span>Element hierher ziehen oder in der Palette antippen</span>
          </li>
        </ol>
      </section>
      <AdmButton v-if="!readonly" variant="ghost" icon="pi pi-plus" @click="emit('add-section')">Abschnitt hinzufügen</AdmButton>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AdmButton from '../atoms/AdmButton.vue'
import type { ElementType, FormElement, FormSchema } from '@/types/admissions'
import { ELEMENT_LABELS, PALETTE } from '@/utils/admissionSchema'

interface Props {
  schema: FormSchema
  activePage: number
  selectedId: string | null
  selectedSection: number | null
  issues: Map<string, string[]>
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), { readonly: false })
const emit = defineEmits<{
  (e: 'select', elementId: string): void
  (e: 'select-page', page: number): void
  (e: 'select-section', section: number): void
  (e: 'move', elementId: string, step: -1 | 1): void
  (e: 'add-page'): void
  (e: 'add-section'): void
}>()

const page = computed(() => props.schema.pages[props.activePage])

function isSectionSelected(sectionIndex: number) {
  return props.selectedId === null && props.selectedSection === sectionIndex
}

function iconFor(type: ElementType) {
  return PALETTE.find((entry) => entry.type === type)?.icon ?? 'pi pi-box'
}

function summary(element: FormElement) {
  if (element.type === 'richtext') return (element.html ?? '').replace(/<[^>]+>/g, ' ').trim().slice(0, 80) || 'Textbaustein'
  if (element.type === 'divider') return '—'
  return element.label || element.key || ELEMENT_LABELS[element.type]
}
</script>

<style scoped>
.canvas {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.canvas__pages {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5);
  align-items: center;
}

.canvas__page-tab {
  min-height: var(--jf-touch-target, 44px);
  padding: 0 var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  cursor: pointer;
}

.canvas__page-tab--active {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
  font-weight: var(--jf-weight-semibold);
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

.canvas__section--selected {
  border-color: var(--jf-color-primary);
}

.canvas__section-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--jf-space-1);
}

.canvas__section-title {
  border: 0;
  background: none;
  padding: 0;
  color: var(--jf-color-text);
  font: inherit;
  font-weight: var(--jf-weight-semibold);
  font-size: var(--jf-text-md);
  cursor: pointer;
  text-align: left;
}

.canvas__count {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.canvas__list {
  list-style: none;
  margin: var(--jf-space-1) 0 0;
  padding: 0;
}

.canvas__item {
  display: flex;
  align-items: stretch;
  gap: var(--jf-space-0-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
}

.canvas__item--selected {
  border-color: var(--jf-color-primary);
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.canvas__item--issue {
  border-left: 4px solid var(--jf-color-warning);
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
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  min-height: var(--jf-touch-target, 44px);
  padding: var(--jf-space-1);
  border: 0;
  background: none;
  color: var(--jf-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.canvas__type {
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.canvas__label {
  font-weight: var(--jf-weight-medium);
}

.canvas__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5);
}

.canvas__badge {
  padding: 0 0.45rem;
  border-radius: 999px;
  background: var(--jf-color-ground);
  font-size: var(--jf-text-xs);
}

.canvas__badge--target {
  font-family: var(--jf-font-mono);
}

.canvas__issue {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-warning);
}

.canvas__actions {
  display: flex;
  align-items: center;
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
  height: 36px;
  background: var(--jf-color-selected);
  outline: 2px dashed var(--jf-color-primary);
}
</style>
