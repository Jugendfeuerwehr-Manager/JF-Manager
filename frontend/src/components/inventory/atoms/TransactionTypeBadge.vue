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
const severity = computed(() => typeInfo.value.color as 'success' | 'warning' | 'info' | 'danger' | 'secondary' | 'contrast' | undefined)
</script>
