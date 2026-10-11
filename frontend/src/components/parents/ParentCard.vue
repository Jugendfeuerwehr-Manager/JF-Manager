<template>
  <article class="parent-card mobile-entity-card" :aria-label="displayName">
    <div class="mobile-entity-card__header">
      <div class="parent-header">
        <span class="parent-initials" aria-hidden="true">{{ initials }}</span>
        <h3 class="mobile-entity-card__title">{{ displayName }}</h3>
      </div>
      <ParentLinkBadge :parent="parent" />
    </div>

    <dl class="parent-details">
      <div class="parent-details__row">
        <dt><i class="pi pi-envelope" aria-hidden="true"></i>E-Mail</dt>
        <dd><ContactLink kind="email" :value="parent.email" /></dd>
      </div>
      <div class="parent-details__row">
        <dt><i class="pi pi-phone" aria-hidden="true"></i>Telefon</dt>
        <dd><ContactLink kind="phone" :value="parent.phone" /></dd>
      </div>
      <div class="parent-details__row">
        <dt><i class="pi pi-mobile" aria-hidden="true"></i>Mobil</dt>
        <dd><ContactLink kind="phone" :value="parent.mobile" /></dd>
      </div>
      <div v-if="parentAddress" class="parent-details__row">
        <dt><i class="pi pi-map-marker" aria-hidden="true"></i>Adresse</dt>
        <dd>{{ parentAddress }}</dd>
      </div>
    </dl>

    <div class="mobile-entity-card__actions">
      <Button label="Bearbeiten" icon="pi pi-pencil" outlined class="parent-card__edit" :aria-label="`${displayName} bearbeiten`" @click="$emit('edit', parent)" />
      <Button
        icon="pi pi-trash"
        severity="danger"
        outlined
        :aria-label="`${displayName} löschen`"
        @click="$emit('delete', parent)"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import ContactLink from '@/components/common/ContactLink.vue'
import ParentLinkBadge from '@/components/parents/ParentLinkBadge.vue'
import type { Parent } from '@/types/parents'

interface Props {
  parent: Parent
}

const props = defineProps<Props>()

defineEmits<{
  edit: [parent: Parent]
  delete: [parent: Parent]
}>()

const displayName = computed(() => props.parent.full_name || `${props.parent.name} ${props.parent.lastname}`.trim())

const initials = computed(() => `${props.parent.name?.[0] ?? ''}${props.parent.lastname?.[0] ?? ''}`.toUpperCase() || '?')

const parentAddress = computed(() => {
  const parts = []
  if (props.parent.street) parts.push(props.parent.street)
  if (props.parent.zip_code || props.parent.city) {
    parts.push(`${props.parent.zip_code} ${props.parent.city}`.trim())
  }
  return parts.join(', ')
})
</script>

<style scoped>
.parent-header {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  min-width: 0;
}

.parent-initials {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
  font-weight: var(--jf-weight-bold);
}

.parent-details {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
}

.parent-details__row {
  display: grid;
  grid-template-columns: 7rem minmax(0, 1fr);
  align-items: center;
  gap: var(--jf-space-1);
  min-height: 32px;
}

.parent-details dt {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
}

.parent-details dd {
  margin: 0;
  min-width: 0;
}

.parent-card__edit {
  flex: 1;
}

.mobile-entity-card__actions :deep(.p-button) {
  min-height: var(--jf-touch-target);
  min-width: var(--jf-touch-target);
}
</style>
