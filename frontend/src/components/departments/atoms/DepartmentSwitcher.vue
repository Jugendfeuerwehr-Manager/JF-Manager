<template>
  <div v-if="showSwitcher" class="department-switcher">
    <Button
      v-if="compact"
      :label="compactLabel"
      :icon="selectedDeptId === null ? 'pi pi-globe' : 'pi pi-building'"
      size="small"
      severity="secondary"
      outlined
      class="dept-compact-button"
      @click="toggleCompactMenu"
    />

    <Select
      v-else
      v-model="selectedDeptId"
      :options="options"
      option-label="label"
      option-value="value"
      :placeholder="'Abteilung wählen'"
      class="dept-select"
      @change="onSelect"
    >
      <template #value="{ value }">
        <div v-if="value === null" class="dept-option">
          <i class="pi pi-globe dept-icon" />
          <span>Alle Abteilungen</span>
        </div>
        <div v-else class="dept-option">
          <span class="dept-color-dot" :style="{ backgroundColor: colorFor(value) }" />
          <i class="pi pi-building dept-icon" />
          <span>{{ labelFor(value) }}</span>
        </div>
      </template>
      <template #option="{ option }">
        <div class="dept-option">
          <span v-if="option.value !== null" class="dept-color-dot" :style="{ backgroundColor: option.color || '#64748B' }" />
          <i :class="['dept-icon', option.value === null ? 'pi pi-globe' : 'pi pi-building']" />
          <span>{{ option.label }}</span>
        </div>
      </template>
    </Select>

    <Menu ref="compactMenu" :model="compactMenuItems" popup class="dept-compact-menu" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import { useDepartmentsStore } from '@/stores/departments'
import { useAuthStore } from '@/stores/auth'

withDefaults(
  defineProps<{
    compact?: boolean
  }>(),
  {
    compact: false,
  },
)

const departmentsStore = useDepartmentsStore()
const authStore = useAuthStore()
const compactMenu = ref()

// Mirror the store value locally so Select has a reactive v-model
const selectedDeptId = ref<number | null>(departmentsStore.activeDepartmentId)

// Keep local ref in sync when store changes externally
watch(
  () => departmentsStore.activeDepartmentId,
  (v) => {
    selectedDeptId.value = v
  },
)

const isOrgWide = computed(() => authStore.user?.has_org_wide_access ?? false)

const showSwitcher = computed(
  () => isOrgWide.value || departmentsStore.departments.length > 0,
)

interface Option {
  label: string
  value: number | null
  color?: string
}

const options = computed<Option[]>(() => {
  const depts = departmentsStore.departments.map((d) => ({
    label: `${d.name} (${d.code})`,
    value: d.id,
    color: d.color,
  }))
  if (isOrgWide.value) {
    return [{ label: 'Alle Abteilungen', value: null }, ...depts]
  }
  return depts
})

function labelFor(id: number | null): string {
  if (id === null) return 'Alle Abteilungen'
  const dept = departmentsStore.departments.find((d) => d.id === id)
  return dept ? `${dept.name} (${dept.code})` : ''
}

function colorFor(id: number | null): string {
  if (id === null) return '#64748B'
  return departmentsStore.departments.find((d) => d.id === id)?.color || '#64748B'
}

function onSelect() {
  departmentsStore.setActiveDepartment(selectedDeptId.value)
}

const compactLabel = computed(() => {
  const label = labelFor(selectedDeptId.value)
  return label.length > 10 ? `${label.slice(0, 10)}…` : label
})

const compactMenuItems = computed<MenuItem[]>(() =>
  options.value.map((option) => ({
    label: option.label,
    icon: option.value === null ? 'pi pi-globe' : 'pi pi-building',
    command: () => {
      selectedDeptId.value = option.value
      onSelect()
    },
  })),
)

function toggleCompactMenu(event: Event) {
  compactMenu.value?.toggle(event)
}
</script>

<style scoped>
.department-switcher {
  display: flex;
  align-items: center;
}

.dept-select {
  min-width: 180px;
  font-size: 0.875rem;
}

.dept-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.dept-icon {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.dept-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 1px solid var(--surface-border);
  display: inline-block;
}

.dept-compact-button {
  max-width: 120px;
  min-width: 0;
  flex-shrink: 1;
}

.dept-compact-button :deep(.p-button-label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dept-compact-menu {
  min-width: 210px;
}
</style>
