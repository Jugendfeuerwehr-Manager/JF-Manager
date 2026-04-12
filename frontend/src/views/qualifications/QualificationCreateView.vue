<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import QualificationForm from '@/components/qualifications/organisms/QualificationForm.vue'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'

const router = useRouter()
const qualificationsStore = useQualificationsStore()
const toast = useToast()

const showForm = ref(false)

onMounted(async () => {
  // Pre-load data needed for the form
  await Promise.all([
    qualificationsStore.fetchQualificationTypes(),
  ])
})

const handleFormSuccess = async (qualificationId: number) => {
  showForm.value = false
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: 'Qualifikation erfolgreich erstellt',
    life: 3000
  })
  // Navigate to the detail view of the newly created qualification
  router.push({ name: 'qualification-detail', params: { id: String(qualificationId) } })
}

const handleFormCancel = () => {
  showForm.value = false
}
</script>

<template>
  <div class="p-4">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Neue Qualifikation</h1>
      <Button
        label="Zurück"
        icon="pi pi-arrow-left"
        severity="secondary"
        @click="router.push('/qualifications')"
      />
    </div>

    <QualificationForm
      @success="handleFormSuccess"
      @cancel="handleFormCancel"
    />
  </div>
</template>
