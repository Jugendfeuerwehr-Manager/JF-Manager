<template>
  <Badge :value="quantity" :severity="severityClass" :class="{ 'zero-stock': quantity === 0 }" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Badge from 'primevue/badge'

interface Props {
  quantity: number
  lowThreshold?: number
}

const props = withDefaults(defineProps<Props>(), {
  lowThreshold: 5
})

const severityClass = computed(() => {
  if (props.quantity === 0) return 'danger'
  if (props.quantity <= props.lowThreshold) return 'warning'
  return 'success'
})
</script>

<style scoped>
.zero-stock {
  opacity: 0.6;
}
</style>
