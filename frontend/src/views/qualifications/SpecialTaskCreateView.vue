<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import SpecialTaskForm from '@/components/qualifications/organisms/SpecialTaskForm.vue'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'

const router = useRouter()
const qualificationsStore = useQualificationsStore()
const toast = useToast()

onMounted(async () => {
  // Pre-load data needed for the form
  await qualificationsStore.fetchSpecialTaskTypes()
})

const handleFormSuccess = async (taskId: number) => {
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: 'Sonderaufgabe erfolgreich erstellt',
    life: 3000
  })
  // Navigate to the detail view of the newly created special task
  router.push({ name: 'specialtask-detail', params: { id: String(taskId) } })
}

const handleFormCancel = () => {
  router.push('/qualifications')
}
</script>

<template>
  <div class="p-4">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Neue Sonderaufgabe</h1>
      <Button
        label="Zurück"
        icon="pi pi-arrow-left"
        severity="secondary"
        @click="router.push('/qualifications')"
      />
    </div>

    <SpecialTaskForm
      @success="handleFormSuccess"
      @cancel="handleFormCancel"
    />
  </div>
</template>
