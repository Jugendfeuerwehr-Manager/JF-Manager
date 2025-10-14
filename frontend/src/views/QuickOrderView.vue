<template>
  <div class="quick-order-wrapper">
    <QuickOrder
      @success="handleSuccess"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import QuickOrder from '@/components/orders/QuickOrderView.vue'

const router = useRouter()
const toast = useToast()

function handleSuccess(orderId: number) {
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: 'Schnellbestellung wurde erstellt',
    life: 3000
  })
  
  // Navigate to order detail
  router.push(`/orders/${orderId}`)
}

function handleCancel() {
  router.push('/orders')
}
</script>

<style scoped>
.quick-order-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}
</style>
