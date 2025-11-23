<template>
  <div 
    class="status-badge"
    :style="badgeStyle"
  >
    <i v-if="icon" :class="icon" class="status-badge__icon"></i>
    <span class="status-badge__text">{{ statusName }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  statusName: string
  statusColor: string
  statusCode?: string
  variant?: 'filled' | 'outlined'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'outlined'
})

// Map status codes to icons
const icon = computed(() => {
  if (!props.statusCode) return undefined
  
  const iconMap: Record<string, string> = {
    'NEW': 'pi pi-plus-circle',
    'pending': 'pi pi-clock',
    'ORDERED': 'pi pi-shopping-cart',
    'ordered': 'pi pi-shopping-cart',
    'RECEIVED': 'pi pi-inbox',
    'received': 'pi pi-inbox',
    'ready': 'pi pi-check',
    'DELIVERED': 'pi pi-check-circle',
    'delivered': 'pi pi-check-circle',
    'CANCELLED': 'pi pi-times-circle',
    'cancelled': 'pi pi-times-circle',
    'defective': 'pi pi-exclamation-triangle'
  }
  
  return iconMap[props.statusCode]
})

const badgeStyle = computed(() => {
  if (props.variant === 'filled') {
    // Determine text color based on background brightness
    const color = props.statusColor.replace('#', '')
    const r = parseInt(color.substr(0, 2), 16)
    const g = parseInt(color.substr(2, 2), 16)
    const b = parseInt(color.substr(4, 2), 16)
    const brightness = (r * 299 + g * 587 + b * 114) / 1000
    const textColor = brightness > 128 ? '#000000' : '#FFFFFF'
    
    return {
      backgroundColor: props.statusColor,
      borderColor: props.statusColor,
      color: textColor
    }
  }
  
  // Outlined variant
  return {
    backgroundColor: 'transparent',
    borderColor: props.statusColor,
    color: props.statusColor
  }
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.65rem;
  border-radius: 1rem;
  border: 1.5px solid;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.status-badge__icon {
  font-size: 0.75rem;
}

.status-badge__text {
  line-height: 1;
}
</style>
