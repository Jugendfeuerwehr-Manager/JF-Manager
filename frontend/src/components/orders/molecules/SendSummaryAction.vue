<template>
  <div v-if="newOrdersCount > 0" class="send-summary-action">
    <Button
      :label="computedLabel"
      :icon="buttonIcon"
      :severity="buttonSeverity"
      :size="buttonSize"
      :disabled="newOrdersCount === 0"
      @click="openDialog"
      v-tooltip.bottom="tooltip"
      class="send-summary-action__trigger"
    />

    <SendSummaryDialog
      v-model:visible="dialogVisible"
      :new-orders-count="newOrdersCount"
      @success="handleSuccess"
      @error="handleError"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import SendSummaryDialog from '@/components/orders/molecules/SendSummaryDialog.vue'

interface Props {
  newOrdersCount: number
  buttonLabel?: string
  buttonSeverity?: string
  buttonSize?: 'small' | 'large' | undefined
  buttonIcon?: string
  tooltip?: string
}

const props = withDefaults(defineProps<Props>(), {
  buttonSeverity: 'info',
  buttonSize: 'small',
  buttonIcon: 'pi pi-send',
  tooltip: 'Alle neuen Bestellungen gesammelt versenden'
})

const emit = defineEmits<{
  success: []
  error: [error: unknown]
}>()

const dialogVisible = ref(false)

const computedLabel = computed(() => {
  return props.buttonLabel ?? `An Gerätewart senden (${props.newOrdersCount})`
})

const buttonSeverity = computed(() => props.buttonSeverity)
const buttonIcon = computed(() => props.buttonIcon)
const buttonSize = computed(() => props.buttonSize)
const tooltip = computed(() => props.tooltip)
const newOrdersCount = computed(() => props.newOrdersCount)

watch(newOrdersCount, (count) => {
  if (count === 0 && dialogVisible.value) {
    dialogVisible.value = false
  }
})

function openDialog() {
  dialogVisible.value = true
}

function handleSuccess() {
  emit('success')
  dialogVisible.value = false
}

function handleError(error: unknown) {
  emit('error', error)
}
</script>

<style scoped>
.send-summary-action__trigger {
  white-space: nowrap;
}
</style>
