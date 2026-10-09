<template>
  <Card class="filter-card">
    <template #content>
      <div id="member-filter-fields" class="filter-grid">
        <div class="filter-search-wrap" :class="{ 'filter-search-wrap--active': mobileSearchMode }">
          <IconField class="filter-search-field">
            <InputIcon class="pi pi-search" />
            <InputText
              v-model="localFilters.search"
              placeholder="Suchen..."
              class="w-full filter-control"
              @focus="emit('search-focus')"
              @input="onFilterChange"
              @keydown.esc="emit('search-esc')"
            />
          </IconField>
          <Button
            v-if="isMobile && !mobileSearchMode"
            :label="activeFilterCount ? `Filter (${activeFilterCount})` : 'Filter'"
            icon="pi pi-filter"
            :severity="activeFilterCount ? 'primary' : 'secondary'"
            outlined
            aria-controls="member-filter-fields"
            :aria-expanded="filtersOpen"
            @click="filtersOpen = !filtersOpen"
          />
        </div>

        <Select
          v-if="showFields"
          v-model="localFilters.status"
          :options="statuses"
          option-label="name"
          option-value="id"
          placeholder="Status filtern"
          show-clear
          class="w-full filter-control"
          @change="onFilterChange"
        />

        <Select
          v-if="showFields"
          v-model="localFilters.group"
          :options="groups"
          option-label="name"
          option-value="id"
          placeholder="Gruppe filtern"
          show-clear
          class="w-full filter-control"
          @change="onFilterChange"
        />

        <Select
          v-if="showFields"
          v-model="localFilters.gender"
          :options="genderOptions"
          option-label="label"
          option-value="value"
          placeholder="Geschlecht filtern"
          show-clear
          class="w-full filter-control"
          @change="onFilterChange"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Button from 'primevue/button'
import { useMobile } from '@/composables/useMobile'
import Card from 'primevue/card'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import type { MemberFilters } from '@/types/members'
import type { Status, Group } from '@/types/members'

interface Props {
  filters: MemberFilters
  statuses: Status[]
  groups: Group[]
  mobileSearchMode?: boolean
}

const props = withDefaults(defineProps<Props>(), { mobileSearchMode: false })

const emit = defineEmits<{
  'update:filters': [filters: MemberFilters]
  'filter-change': []
  'search-focus': []
  'search-esc': []
}>()

const genderOptions = [
  { label: 'Männlich', value: 'male' },
  { label: 'Weiblich', value: 'female' },
  { label: 'Divers', value: 'diverse' },
]

const localFilters = reactive<MemberFilters>({ ...props.filters })

watch(
  () => props.filters,
  (next) => Object.assign(localFilters, next),
  { deep: true },
)

const { isMobile } = useMobile()
const filtersOpen = ref(false)
const activeFilterCount = computed(() => [localFilters.status, localFilters.group, localFilters.gender].filter((value) => value !== null && value !== undefined && value !== '').length)
// On phones the selects stay folded away so the list starts right below the search.
const showFields = computed(() => !props.mobileSearchMode && (!isMobile.value || filtersOpen.value))

function onFilterChange() {
  emit('update:filters', { ...localFilters })
  emit('filter-change')
}
</script>

<style scoped>
.filter-card :deep(.p-card-body) {
  padding: var(--jf-space-2);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.filter-search-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-search-field {
  flex: 1;
}

@media (max-width: 768px) {
  .filter-card :deep(.p-card-body) {
    padding: var(--jf-space-1-5);
  }

  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .filter-search-wrap {
    grid-column: 1 / -1;
  }

  .filter-search-wrap--active {
    margin-bottom: 0.25rem;
  }

  .filter-search-field,
  .filter-control {
    width: 100%;
  }

  .filter-search-field :deep(.p-inputtext),
  .filter-control :deep(.p-inputtext),
  .filter-control :deep(.p-dropdown) {
    min-height: 2.35rem;
  }

  .filter-search-field :deep(.p-iconfield .p-inputtext) {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
  }

  .filter-control :deep(.p-dropdown-label) {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
  }
}

@media (max-width: 420px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  /* card padding 0.75rem -> 0.5rem, field gap 0.55rem -> 0.5rem */
  .filter-card :deep(.p-card-body) {
    padding: var(--jf-space-1);
  }

  .filter-grid {
    gap: var(--jf-space-1);
  }
}
</style>
