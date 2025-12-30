<template>
  <Card class="recipients-list" v-if="recipients.length > 0">
    <template #header>
      <div class="recipients-header">
        <h3>
          <i class="pi pi-users"></i>
          Empfänger ({{ recipients.length }})
        </h3>
        <Button
          :icon="isExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          :label="isExpanded ? 'Einklappen' : 'Anzeigen'"
          @click="isExpanded = !isExpanded"
          outlined
          size="small"
        />
      </div>
    </template>
    <template #content>
      <div v-if="isExpanded">
        <DataTable
          :value="recipients"
          :rows="10"
          :paginator="recipients.length > 10"
          class="recipients-table"
          :loading="loading"
        >
          <Column field="name" header="Name" sortable />
          <Column field="email" header="E-Mail" sortable />
          <Column field="source" header="Quelle" sortable>
            <template #body="{ data }">
              <Tag
                :value="data.source"
                :severity="data.source === 'Mitglied' ? 'info' : 'secondary'"
              />
            </template>
          </Column>
        </DataTable>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

interface Recipient {
  name: string
  email: string
  source: string
}

interface Props {
  recipients: Recipient[]
  loading?: boolean
}

defineProps<Props>()

const isExpanded = ref(false)
</script>

<style scoped>
.recipients-list {
  margin-top: 1rem;
}

.recipients-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
}

.recipients-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color);
}

.recipients-table {
  margin-top: 1rem;
}

@media (max-width: 768px) {
  .recipients-header {
    padding: 0.75rem;
  }
  
  .recipients-header h3 {
    font-size: 1rem;
  }
}
</style>
