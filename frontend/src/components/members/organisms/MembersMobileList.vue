<template>
  <ResponsiveList
    :items="members"
    :loading="loading"
    :rows="rows"
    :paginator="totalRecords > rows"
    :total-records="totalRecords"
    :lazy="true"
    item-key="id"
    @page="emit('page', $event)"
  >
    <template #item="{ item: member }">
      <Card
        class="member-card mobile-entity-card"
        @click="emit('view', member)"
      >
        <template #content>
          <div class="mobile-entity-card__header">
            <div>
              <h3 class="mobile-entity-card__title">{{ member.full_name }}</h3>
              <p class="mobile-entity-card__meta">
                {{ formatDate(member.birthday) }} · {{ member.age }} Jahre
              </p>
            </div>
            <Tag
              v-if="member.status"
              :value="member.status.name"
              :style="{ backgroundColor: member.status.color, color: 'white' }"
            />
          </div>

          <ParentContacts :member="member" variant="compact" />

          <div class="mobile-entity-card__actions" @click.stop>
            <Button
              label="Ansehen"
              icon="pi pi-eye"
              size="small"
              outlined
              class="member-card-action"
              aria-label="Mitglied ansehen"
              @click="emit('view', member)"
            />
            <Button
              label="Bearbeiten"
              icon="pi pi-pencil"
              size="small"
              outlined
              severity="secondary"
              class="member-card-action"
              aria-label="Mitglied bearbeiten"
              @click="emit('edit', member)"
            />
            <Button
              icon="pi pi-trash"
              size="small"
              outlined
              severity="danger"
              class="member-card-action"
              aria-label="Mitglied löschen"
              @click="emit('delete', member)"
            />
          </div>
        </template>
      </Card>
    </template>

    <template #empty>
      <div class="mobile-list-empty">
        <i class="pi pi-users"></i>
        <p>Keine Mitglieder gefunden</p>
      </div>
    </template>
  </ResponsiveList>
</template>

<script setup lang="ts">
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import ParentContacts from '@/components/members/ParentContacts.vue'
import type { Member } from '@/types/members'

interface Props {
  members: Member[]
  loading: boolean
  rows: number
  totalRecords: number
}

defineProps<Props>()

const emit = defineEmits<{
  page: [event: { first: number; rows: number }]
  view: [member: Member]
  edit: [member: Member]
  delete: [member: Member]
}>()

function formatDate(dateString: string | null) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
</script>

<style scoped>
.member-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border-radius: calc(var(--border-radius) - 2px);
}

.member-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

@media (max-width: 768px) {
  .member-card .mobile-entity-card__actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .member-card .member-card-action :deep(.p-button-label) {
    display: none;
  }

  .member-card .member-card-action :deep(.p-button-icon) {
    margin-right: 0;
  }

  .member-card .member-card-action :deep(.p-button) {
    justify-content: center;
    min-height: 2.15rem;
    padding: 0.35rem;
  }

  .member-card :deep(.parent-contacts--compact) {
    margin-top: -0.15rem;
  }
}
</style>
