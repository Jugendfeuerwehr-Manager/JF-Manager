<template>
  <a v-if="href" class="contact-link" :href="href" @click.stop>{{ label || trimmed }}</a>
  <span v-else class="contact-link contact-link--empty">–</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  value?: string | null
  kind: 'phone' | 'email'
  label?: string
}

const props = withDefaults(defineProps<Props>(), { value: '', label: '' })

const trimmed = computed(() => (props.value ?? '').trim())

/** tel: keeps only digits and a leading plus; mailto: uses the trimmed address. */
const href = computed(() => {
  if (!trimmed.value) return ''
  if (props.kind === 'email') return `mailto:${trimmed.value}`
  const digits = trimmed.value.replace(/[^\d+]/g, '')
  const normalised = (digits.startsWith('+') ? '+' : '') + digits.replace(/\+/g, '')
  return normalised ? `tel:${normalised}` : ''
})
</script>

<style scoped>
/* Visibly a link (colour and underline), so it reads as clickable without relying on colour alone. */
.contact-link {
  overflow-wrap: anywhere;
}

a.contact-link {
  color: var(--p-primary-color);
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
}

a.contact-link:hover {
  text-decoration-thickness: 2px;
}

a.contact-link:focus-visible {
  outline: 2px solid var(--p-primary-color, currentColor);
  outline-offset: 2px;
  border-radius: 2px;
  text-decoration: underline;
}
</style>
