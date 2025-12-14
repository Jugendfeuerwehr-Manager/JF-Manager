<template>
  <Card class="member-loan-card" :class="{ 'expanded': expanded }">
    <template #header>
      <div class="card-header" @click="expanded = !expanded">
        <div class="member-info">
          <Avatar :label="initials" size="large" shape="circle" />
          <div class="member-details">
            <h4>{{ loan.member_name }}</h4>
            <span class="item-count">{{ loan.total_items }} Artikel ausgeliehen</span>
          </div>
        </div>
        <Button
          :icon="expanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          text
          rounded
          @click.stop="expanded = !expanded"
        />
      </div>
    </template>
    <template #content>
      <transition name="slide">
        <div v-if="expanded" class="loan-items">
          <DataTable :value="loan.items" :paginator="loan.items.length > 5" :rows="5" size="small">
            <Column field="item_name" header="Artikel">
              <template #body="{ data }">
                {{ data.variant_display || data.item_name || 'Unbekannt' }}
              </template>
            </Column>
            <Column field="category_name" header="Kategorie">
              <template #body="{ data }">
                <Tag v-if="data.category_name" :value="data.category_name" severity="secondary" />
                <span v-else class="text-muted">-</span>
              </template>
            </Column>
            <Column field="quantity" header="Anzahl" style="width: 100px; text-align: center">
              <template #body="{ data }">
                <StockBadge :quantity="data.quantity" />
              </template>
            </Column>
            <Column header="Aktionen" style="width: 100px">
              <template #body="{ data }">
                <Button
                  icon="pi pi-replay"
                  size="small"
                  text
                  rounded
                  severity="success"
                  title="Rückgabe"
                  @click="$emit('return', data)"
                />
              </template>
            </Column>
          </DataTable>
        </div>
      </transition>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import StockBadge from '../atoms/StockBadge.vue'
import type { MemberLoan } from '@/types/inventory'

interface Props {
  loan: MemberLoan
  initialExpanded?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  initialExpanded: false
})

defineEmits<{
  return: [item: MemberLoan['items'][0]]
}>()

const expanded = ref(props.initialExpanded)

const initials = computed(() => {
  const parts = props.loan.member_name.split(' ')
  const first = parts[0]
  const last = parts[parts.length - 1]
  if (parts.length >= 2 && first && last && first.length > 0 && last.length > 0) {
    return (first.charAt(0) + last.charAt(0)).toUpperCase()
  }
  return props.loan.member_name.substring(0, 2).toUpperCase()
})
</script>

<style scoped>
.member-loan-card {
  margin-bottom: 1rem;
  transition: all 0.3s ease;
}

.member-loan-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  cursor: pointer;
  background: var(--surface-ground);
  border-radius: var(--border-radius) var(--border-radius) 0 0;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.member-details h4 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--text-color);
}

.item-count {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.loan-items {
  padding: 0.5rem 0;
}

.text-muted {
  color: var(--text-color-secondary);
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
