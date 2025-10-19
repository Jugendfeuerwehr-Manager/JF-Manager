<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SpecialTaskForm from '@/components/qualifications/organisms/SpecialTaskForm.vue'
import AttachmentsSection from '@/components/qualifications/organisms/AttachmentsSection.vue'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const taskId = computed(() => Number(route.params.id))

function handleSuccess(id: number) {
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: 'Sonderaufgabe wurde aktualisiert.',
    life: 3000
  })
  router.push(`/qualifications/specialtasks/${id}`)
}

function handleCancel() {
  if (taskId.value) {
    router.push(`/qualifications/specialtasks/${taskId.value}`)
  } else {
    router.push('/qualifications')
  }
}
</script>

<template>
  <div class="edit-view">
    <div class="view-header">
      <div>
        <h1 class="title">Sonderaufgabe bearbeiten</h1>
        <p class="subtitle">Passe die Details dieser Aufgabe an.</p>
      </div>
      <Button
        label="Zurück"
        icon="pi pi-arrow-left"
        severity="secondary"
        outlined
        @click="handleCancel"
      />
    </div>

    <SpecialTaskForm
      v-if="taskId"
      :task-id="taskId"
      @success="handleSuccess"
      @cancel="handleCancel"
    />

    <AttachmentsSection
      v-if="taskId"
      :source-id="taskId"
      source-type="specialTask"
    />

    <div v-else class="invalid-state">
      <i class="pi pi-exclamation-triangle"></i>
      <p>Die Sonderaufgabe konnte nicht gefunden werden.</p>
      <Button label="Zur Übersicht" @click="router.push('/qualifications')" />
    </div>
  </div>
</template>

<style scoped>
.edit-view {
  padding: 1.5rem;
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.title {
  margin: 0;
  font-size: 1.75rem;
}

.subtitle {
  margin: 0;
  color: var(--text-color-secondary);
}

.invalid-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  border: 1px dashed var(--surface-border);
  border-radius: var(--border-radius);
  color: var(--text-color-secondary);
}

.invalid-state i {
  font-size: 2rem;
}

@media (max-width: 768px) {
  .edit-view {
    padding: 1rem;
  }

  .view-header {
    flex-direction: column-reverse;
    align-items: flex-start;
  }
}
</style>
