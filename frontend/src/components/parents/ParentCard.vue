<template>
  <Card class="parent-card mobile-entity-card">
    <template #content>
      <div class="mobile-entity-card__header">
        <div class="parent-header">
          <Avatar
            :label="parentInitials"
            size="large"
            shape="circle"
            :style="{ backgroundColor: avatarColor, color: 'white' }"
          />
          <div class="parent-info">
            <h3 class="mobile-entity-card__title">{{ parent.full_name || `${parent.name} ${parent.lastname}` }}</h3>
          </div>
        </div>
        <Tag
          v-if="parent.children && parent.children.length === 0"
          value="Kein Kind"
          severity="warn"
          v-tooltip.top="'Kein Mitglied mit diesem Elternteil verknüpft'"
        />
      </div>

      <div class="mobile-entity-card__section parent-details">
        <div class="mobile-entity-card__row">
          <span class="mobile-entity-card__label">
            <i class="pi pi-envelope"></i>
            E-Mail
          </span>
          <span class="mobile-entity-card__value">{{ parent.email || '-' }}</span>
        </div>

        <div class="mobile-entity-card__row">
          <span class="mobile-entity-card__label">
            <i class="pi pi-phone"></i>
            Telefon
          </span>
          <span class="mobile-entity-card__value">{{ parent.phone || '-' }}</span>
        </div>

        <div class="mobile-entity-card__row">
          <span class="mobile-entity-card__label">
            <i class="pi pi-mobile"></i>
            Mobil
          </span>
          <span class="mobile-entity-card__value">{{ parent.mobile || '-' }}</span>
        </div>

        <div v-if="parentAddress" class="mobile-entity-card__row">
          <span class="mobile-entity-card__label">
            <i class="pi pi-map-marker"></i>
            Adresse
          </span>
          <span class="mobile-entity-card__value">{{ parentAddress }}</span>
        </div>
      </div>

      <div class="mobile-entity-card__actions">
        <Button
          label="Bearbeiten"
          icon="pi pi-pencil"
          outlined
          @click="$emit('edit', parent)"
          class="flex-1"
        />
        <Button
          icon="pi pi-trash"
          severity="danger"
          outlined
          @click="$emit('delete', parent)"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Parent } from '@/types/api'
import Card from 'primevue/card'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

interface Props {
  parent: Parent
}

const props = defineProps<Props>()

defineEmits<{
  edit: [parent: Parent]
  delete: [parent: Parent]
}>()

const parentInitials = computed(() => {
  const first = props.parent.name?.[0] || ''
  const last = props.parent.lastname?.[0] || ''
  return `${first}${last}`.toUpperCase()
})

const parentAddress = computed(() => {
  const parts = []
  if (props.parent.street) parts.push(props.parent.street)
  if (props.parent.zip_code || props.parent.city) {
    parts.push(`${props.parent.zip_code} ${props.parent.city}`.trim())
  }
  return parts.join(', ')
})

const avatarColor = computed(() => {
  const colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b']
  const index = (props.parent.name?.charCodeAt(0) || 0) % colors.length
  return colors[index]
})
</script>

<style scoped>
.parent-card {
  height: 100%;
}

.parent-card :deep(.p-card-body) {
  padding: 0;
}

.parent-card :deep(.p-card-content) {
  padding: 0;
}

.parent-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.parent-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.parent-details {
  gap: 0.75rem;
}

.flex-1 {
  flex: 1;
}
</style>
