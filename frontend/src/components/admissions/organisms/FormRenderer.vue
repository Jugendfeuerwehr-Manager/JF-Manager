<template>
  <div class="renderer">
    <section v-for="page in shownPages" :key="page.id" class="renderer__page" :aria-labelledby="`${idPrefix}-${page.id}`">
      <h2 :id="`${idPrefix}-${page.id}`" class="renderer__page-title">{{ page.title }}</h2>
      <section v-for="section in page.sections" :key="section.id" class="renderer__section">
        <h3 v-if="section.title" class="renderer__section-title">{{ section.title }}</h3>
        <template v-for="element in section.elements" :key="element.id">
          <FormElementView
            v-if="visible(element)"
            :element="element"
            :model-value="element.key ? modelValue[element.key] : undefined"
            :error="element.key ? errors[element.key] : ''"
            :disabled="disabled"
            :id-prefix="idPrefix"
            @update:model-value="(value) => update(element, value)"
          />
        </template>
      </section>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import FormElementView from '../molecules/FormElementView.vue'
import type { FormElement, FormSchema } from '@/types/admissions'
import { ageOn, allElements, isVisible } from '@/utils/admissionSchema'

interface Props {
  schema: FormSchema
  modelValue: Record<string, unknown>
  errors?: Record<string, string>
  /** index of the page to show; null shows all pages */
  page?: number | null
  disabled?: boolean
  idPrefix?: string
}

const props = withDefaults(defineProps<Props>(), { errors: () => ({}), page: null, disabled: false, idPrefix: 'adm' })
const emit = defineEmits<{ (e: 'update:modelValue', value: Record<string, unknown>): void }>()

const shownPages = computed(() =>
  props.page === null ? props.schema.pages : props.schema.pages.slice(props.page, props.page + 1)
)

const birthdayKey = computed(() => allElements(props.schema).find((element) => element.target === 'member.birthday')?.key)
const age = computed(() => {
  const value = birthdayKey.value ? props.modelValue[birthdayKey.value] : null
  return ageOn(typeof value === 'string' ? value : null)
})

function visible(element: FormElement) {
  return isVisible(element.visible_if, props.modelValue, age.value)
}

function update(element: FormElement, value: unknown) {
  if (!element.key) return
  emit('update:modelValue', { ...props.modelValue, [element.key]: value })
}
</script>

<style scoped>
.renderer,
.renderer__page,
.renderer__section {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.renderer__page + .renderer__page {
  padding-top: var(--jf-space-3);
  border-top: 1px solid var(--jf-color-border);
}

.renderer__page-title {
  margin: 0;
  font-size: var(--jf-text-xl);
}

.renderer__section-title {
  margin: var(--jf-space-1) 0 0;
  font-size: var(--jf-text-md);
  color: var(--jf-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
</style>
