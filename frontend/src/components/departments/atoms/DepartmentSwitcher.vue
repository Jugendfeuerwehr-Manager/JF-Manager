<template>
  <div v-if="showSwitcher" class="department-switcher">
    <Button
      v-if="compact"
      :label="compactLabel"
      :icon="selectedDeptId === null ? 'pi pi-globe' : 'pi pi-building'"
      :aria-label="`Abteilung wechseln, aktuell: ${labelFor(selectedDeptId)}`"
      aria-haspopup="menu"
      severity="secondary"
      outlined
      class="dept-compact-button"
      @click="toggleCompactMenu"
    />

    <Select
      v-else
      v-model="selectValue"
      :options="options"
      option-label="label"
      option-value="value"
      :placeholder="'Abteilung wählen'"
      class="dept-select"
      @change="onSelect"
    >
      <template #value="{ value }">
        <div v-if="value === ALL_VALUE || value === null" class="dept-option">
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
          <span v-if="option.value !== ALL_VALUE" class="dept-color-dot" :style="{ backgroundColor: option.color || '#64748B' }" />
          <i :class="['dept-icon', option.value === ALL_VALUE ? 'pi pi-globe' : 'pi pi-building']" />
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

/**
 * PrimeVue treats null as "empty" and would show the placeholder. The Select
 * therefore uses a sentinel for "Alle Abteilungen"; the store keeps null.
 */
const ALL_VALUE = -1
const selectValue = computed<number>({
  get: () => selectedDeptId.value ?? ALL_VALUE,
  set: (v) => {
    selectedDeptId.value = v === ALL_VALUE || v === null || v === undefined ? null : v
  },
})

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
  value: number
  color?: string
}

const options = computed<Option[]>(() => {
  const depts = departmentsStore.departments.map((d) => ({
    label: `${d.name} (${d.code})`,
    value: d.id,
    color: d.color,
  }))
  if (isOrgWide.value) {
    return [{ label: 'Alle Abteilungen', value: ALL_VALUE }, ...depts]
  }
  return depts
})

function labelFor(id: number | null): string {
  if (id === null || id === ALL_VALUE) return 'Alle Abteilungen'
  const dept = departmentsStore.departments.find((d) => d.id === id)
  return dept ? `${dept.name} (${dept.code})` : ''
}

function colorFor(id: number | null): string {
  if (id === null || id === ALL_VALUE) return '#64748B'
  return departmentsStore.departments.find((d) => d.id === id)?.color || '#64748B'
}

/** Code first, so the distinguishing part survives truncation on narrow screens. */
const compactLabel = computed(() => {
  if (selectedDeptId.value === null) return 'Alle Abteilungen'
  const dept = departmentsStore.departments.find((d) => d.id === selectedDeptId.value)
  return dept ? `${dept.code} · ${dept.name}` : ''
})

function onSelect() {
  departmentsStore.setActiveDepartment(selectedDeptId.value)
}

const compactMenuItems = computed<MenuItem[]>(() =>
  options.value.map((option) => ({
    label: option.label,
    icon: option.value === ALL_VALUE ? 'pi pi-globe' : 'pi pi-building',
    command: () => {
      selectValue.value = option.value
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
  min-width: 0;
}

/* Long department names must not push the Select out of narrow containers (mobile drawer). */
.dept-select {
  min-width: min(180px, 100%);
  max-width: 100%;
  font-size: 0.875rem;
}

.dept-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.dept-option > span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dept-color-dot,
.dept-icon {
  flex: none;
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
  max-width: 100%;
  min-width: 0;
  flex-shrink: 1;
  border-radius: 999px;
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
