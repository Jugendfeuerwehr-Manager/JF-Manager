<template>
  <div class="user-chip-selector">
    <div v-if="searchable" class="search-container">
      <IconField iconPosition="left">
        <InputIcon>
          <i class="pi pi-search" />
        </InputIcon>
        <InputText
          v-model="searchQuery"
          placeholder="Suchen..."
          class="search-input"
        />
      </IconField>
    </div>
    
    <div class="chips-container">
      <Chip
        v-for="user in filteredUsers"
        :key="user.value"
        :label="user.label"
        :class="{ 'chip-selected': isSelected(user.value) }"
        :removable="false"
        @click="toggleSelection(user.value)"
        class="user-chip"
      />
      
      <div v-if="filteredUsers.length === 0" class="empty-state">
        <small>Keine Benutzer gefunden</small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Chip from 'primevue/chip'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'

interface UserOption {
  label: string
  value: number
}

interface Props {
  options: UserOption[]
  modelValue: number[]
  searchable?: boolean
  loading?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: number[]): void
}

const props = withDefaults(defineProps<Props>(), {
  searchable: true,
  loading: false
})

const emit = defineEmits<Emits>()

const searchQuery = ref('')

const filteredUsers = computed(() => {
  if (!searchQuery.value) return props.options
  
  const query = searchQuery.value.toLowerCase()
  return props.options.filter(user => 
    user.label.toLowerCase().includes(query)
  )
})

const isSelected = (userId: number): boolean => {
  return props.modelValue.includes(userId)
}

const toggleSelection = (userId: number) => {
  const currentSelection = [...props.modelValue]
  const index = currentSelection.indexOf(userId)
  
  if (index > -1) {
    // Remove from selection
    currentSelection.splice(index, 1)
  } else {
    // Add to selection
    currentSelection.push(userId)
  }
  
  emit('update:modelValue', currentSelection)
}
</script>

<style scoped>
.user-chip-selector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.search-container {
  width: 100%;
}

.search-input {
  width: 100%;
}

.chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  max-height: 300px;
  overflow-y: auto;
  padding: 0.25rem;
}

.user-chip {
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  background: var(--surface-100);
}

.user-chip:hover {
  background: var(--surface-200);
  transform: translateY(-1px);
}

.chip-selected {
  background: var(--primary-color) !important;
  color: var(--primary-color-text) !important;
  border-color: var(--primary-color) !important;
}

.chip-selected:hover {
  background: var(--primary-600) !important;
}

.empty-state {
  width: 100%;
  text-align: center;
  padding: 1rem;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .chips-container {
    max-height: 200px;
  }
}
</style>
