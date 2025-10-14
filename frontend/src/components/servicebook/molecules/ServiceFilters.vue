<template>
  <div class="service-filters">
    <div class="filter-row">
      <div class="filter-field">
        <label for="search">Suche</label>
        <InputText
          id="search"
          v-model="localFilters.search"
          placeholder="Thema, Beschreibung..."
          @input="emitFilters"
        />
      </div>

      <div class="filter-field">
        <label for="dateFrom">Von</label>
        <Calendar
          id="dateFrom"
          v-model="localFilters.dateFrom"
          dateFormat="dd.mm.yy"
          showIcon
          :showButtonBar="true"
          @update:modelValue="emitFilters"
        />
      </div>

      <div class="filter-field">
        <label for="dateTo">Bis</label>
        <Calendar
          id="dateTo"
          v-model="localFilters.dateTo"
          dateFormat="dd.mm.yy"
          showIcon
          :showButtonBar="true"
          @update:modelValue="emitFilters"
        />
      </div>
    </div>

    <div class="filter-actions">
      <Button
        label="Zurücksetzen"
        icon="pi pi-filter-slash"
        outlined
        size="small"
        @click="handleReset"
      />
      <Button
        label="Filtern"
        icon="pi pi-filter"
        size="small"
        @click="emitFilters"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Calendar from 'primevue/calendar'
import Button from 'primevue/button'
import type { ServiceFilters } from '@/types/servicebook'

interface Props {
  filters: ServiceFilters
}

interface Emits {
  (e: 'update:filters', filters: ServiceFilters): void
  (e: 'apply'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const localFilters = ref<ServiceFilters>({ ...props.filters })

watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = { ...newFilters }
  },
  { deep: true }
)

const emitFilters = () => {
  emit('update:filters', { ...localFilters.value })
  emit('apply')
}

const handleReset = () => {
  localFilters.value = {
    search: undefined,
    topic: undefined,
    place: undefined,
    operations_manager: undefined,
    dateFrom: null,
    dateTo: null
  }
  emitFilters()
}
</script>

<style scoped>
.service-filters {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background: var(--surface-0);
  border-radius: var(--border-radius);
  border: 1px solid var(--surface-border);
}

.filter-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 1rem;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.filter-field label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-color);
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

@media (max-width: 768px) {
  .filter-row {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    justify-content: stretch;
  }

  .filter-actions button {
    flex: 1;
  }
}
</style>
