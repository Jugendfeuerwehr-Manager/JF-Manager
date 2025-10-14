<template>
  <Tag 
    :value="statusName" 
    :style="{ backgroundColor: statusColor, color: textColor }"
    :icon="icon"
    :rounded="true"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'

interface Props {
  statusName: string
  statusColor: string
  statusCode?: string
}

const props = defineProps<Props>()

// Determine text color based on background brightness
const textColor = computed(() => {
  const color = props.statusColor.replace('#', '')
  const r = parseInt(color.substr(0, 2), 16)
  const g = parseInt(color.substr(2, 2), 16)
  const b = parseInt(color.substr(4, 2), 16)
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  return brightness > 128 ? '#000000' : '#FFFFFF'
})

// Map status codes to icons
const icon = computed(() => {
  if (!props.statusCode) return undefined
  
  const iconMap: Record<string, string> = {
    'NEW': 'pi pi-plus-circle',
    'ORDERED': 'pi pi-shopping-cart',
    'RECEIVED': 'pi pi-inbox',
    'DELIVERED': 'pi pi-check-circle',
    'CANCELLED': 'pi pi-times-circle'
  }
  
  return iconMap[props.statusCode]
})
</script>
