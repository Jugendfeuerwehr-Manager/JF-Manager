<template>
  <Tag :severity="severity" :value="label" :icon="icon" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import type { TransactionType } from '@/types/inventory'
import { TRANSACTION_TYPES } from '@/types/inventory'

interface Props {
  type: TransactionType
}

const props = defineProps<Props>()

const typeInfo = computed(() => {
  return TRANSACTION_TYPES.find((t) => t.value === props.type) ?? { value: 'IN' as TransactionType, label: 'Unbekannt', icon: 'pi-question', color: 'secondary' }
})

const label = computed(() => typeInfo.value.label)
const icon = computed(() => `pi ${typeInfo.value.icon}`)
/** PrimeVue 4 calls the warning tone `warn` and has no `primary` severity (that is the default). */
const severity = computed(() => {
  const color = typeInfo.value.color
  if (color === 'warning') return 'warn'
  if (color === 'primary') return undefined
  return color as 'success' | 'info' | 'danger' | 'secondary' | 'contrast'
})
</script>
