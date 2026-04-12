<template>
  <div class="permission-picker">
    <div class="picker-header flex align-items-center gap-2 mb-2">
      <InputText
        v-model="search"
        placeholder="Berechtigungen suchen..."
        size="small"
        class="flex-1"
      />
      <Button
        :label="allSelected ? 'Alle abwählen' : 'Alle wählen'"
        size="small"
        severity="secondary"
        text
        @click="toggleAll"
      />
    </div>

    <div class="permission-categories">
      <Accordion :multiple="true" :value="openPanels">
        <AccordionPanel v-for="cat in filteredCategories" :key="cat.label" :value="cat.label">
          <AccordionHeader>
            <div class="flex align-items-center gap-2 w-full">
              <i :class="cat.icon" />
              <span class="font-medium">{{ cat.label }}</span>
              <Badge
                :value="selectedCountFor(cat)"
                :severity="selectedCountFor(cat) > 0 ? 'success' : 'secondary'"
                class="ml-auto"
              />
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="permission-list">
              <div
                v-for="perm in cat.permissions"
                :key="perm.id"
                class="permission-row flex align-items-center gap-2 py-1"
              >
                <Checkbox
                  :model-value="modelValue.includes(perm.id)"
                  :input-id="`perm-${perm.id}`"
                  binary
                  @update:model-value="(val) => togglePermission(perm.id, val)"
                />
                <label :for="`perm-${perm.id}`" class="flex-1 cursor-pointer permission-label">
                  {{ perm.name }}
                </label>
                <PermissionInfoIcon :description="perm.description || perm.codename" />
              </div>
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>

      <div v-if="filteredCategories.length === 0" class="text-center py-4 text-color-secondary">
        <i class="pi pi-search mr-2" />
        Keine Berechtigungen gefunden
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import PermissionInfoIcon from '@/components/admin/atoms/PermissionInfoIcon.vue'
import type { PermissionCategory } from '@/types/admin'

const props = defineProps<{
  modelValue: number[]
  categories: PermissionCategory[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

const search = ref('')

const openPanels = computed(() =>
  props.categories.map((c) => c.label)
)

const filteredCategories = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return props.categories
  return props.categories
    .map((cat) => ({
      ...cat,
      permissions: cat.permissions.filter(
        (p) => p.name.toLowerCase().includes(q) || p.codename.toLowerCase().includes(q)
      ),
    }))
    .filter((cat) => cat.permissions.length > 0)
})

const allPermIds = computed(() =>
  props.categories.flatMap((c) => c.permissions.map((p) => p.id))
)

const allSelected = computed(
  () => allPermIds.value.length > 0 && allPermIds.value.every((id) => props.modelValue.includes(id))
)

function selectedCountFor(cat: PermissionCategory) {
  return cat.permissions.filter((p) => props.modelValue.includes(p.id)).length
}

function togglePermission(id: number, checked: boolean) {
  const current = new Set(props.modelValue)
  if (checked) {
    current.add(id)
  } else {
    current.delete(id)
  }
  emit('update:modelValue', Array.from(current))
}

function toggleAll() {
  if (allSelected.value) {
    emit('update:modelValue', [])
  } else {
    emit('update:modelValue', [...allPermIds.value])
  }
}
</script>

<style scoped>
.permission-picker {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.permission-categories {
  overflow-y: auto;
  flex: 1;
}

.permission-list {
  max-height: none;
}

.permission-row:hover {
  background: var(--p-content-hover-background);
  border-radius: 4px;
  padding-left: 4px;
}

.permission-label {
  font-size: 0.9rem;
  color: var(--p-text-color);
}
</style>
