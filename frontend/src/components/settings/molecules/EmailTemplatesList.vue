<template>
  <Card>
    <template #title>Vorlagen</template>
    <template #content>
      <div v-if="!templates.length" class="empty-state">
        <i class="pi pi-inbox" style="font-size: 3rem; color: var(--p-text-muted-color)"></i>
        <p>Keine E-Mail-Vorlagen vorhanden</p>
        <Button label="Erste Vorlage erstellen" icon="pi pi-plus" @click="$emit('create')" />
      </div>
      <DataTable v-else :value="templates" class="templates-table">
        <Column field="template_type_display" header="Typ" sortable></Column>
        <Column field="is_active" header="Status" sortable>
          <template #body="{ data }">
            <Tag
              :value="data.is_active ? 'Aktiv' : 'Inaktiv'"
              :severity="data.is_active ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column field="updated_at" header="Aktualisiert" sortable>
          <template #body="{ data }">
            {{ formatDate(data.updated_at) }}
          </template>
        </Column>
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              severity="info"
              @click="$emit('edit', data.id)"
              v-tooltip.top="'Bearbeiten'"
            />
            <Button
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              @click="$emit('delete', data.id)"
              v-tooltip.top="'Löschen'"
            />
          </template>
        </Column>
      </DataTable>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { format } from 'date-fns'
import Button from 'primevue/button'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import type { EmailTemplateList } from '@/types/email-templates'

interface Props {
  templates: EmailTemplateList[]
}

interface Emits {
  (e: 'edit', id: number): void
  (e: 'delete', id: number): void
  (e: 'create'): void
}

defineProps<Props>()
defineEmits<Emits>()

function formatDate(dateString: string): string {
  return format(new Date(dateString), 'dd.MM.yyyy HH:mm')
}
</script>

<style scoped>
.templates-table {
  min-height: 300px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.empty-state p {
  margin: 1rem 0;
}
</style>
