<template>
  <Card>
    <template #content>
      <div class="flex align-items-start gap-3 mb-3">
        <Avatar
          v-if="member.avatar_url"
          :image="member.avatar_url"
          size="xlarge"
          shape="circle"
        />
        <Avatar
          v-else
          :label="memberInitials"
          size="xlarge"
          shape="circle"
          style="background-color: var(--primary-color); color: white"
        />
        
        <div class="flex-1">
          <h3 class="m-0 mb-1">{{ member.full_name }}</h3>
          <Tag v-if="member.status" :value="member.status.name" :style="{ backgroundColor: member.status.color }" />
        </div>
      </div>

      <Divider />

      <div class="flex flex-column gap-2 my-3">
        <div class="flex align-items-center gap-2">
          <i class="pi pi-calendar" style="color: var(--text-color-secondary)"></i>
          <span class="text-color-secondary">Geburtstag:</span>
          <span>{{ formatDate(member.birthday) }}</span>
        </div>

        <div class="flex align-items-center gap-2">
          <i class="pi pi-clock" style="color: var(--text-color-secondary)"></i>
          <span class="text-color-secondary">Alter:</span>
          <span>{{ member.age }} Jahre</span>
        </div>

        <div v-if="member.email" class="flex align-items-center gap-2">
          <i class="pi pi-envelope" style="color: var(--text-color-secondary)"></i>
          <span class="text-color-secondary">E-Mail:</span>
          <span class="text-sm">{{ member.email }}</span>
        </div>

        <div v-if="member.mobile" class="flex align-items-center gap-2">
          <i class="pi pi-phone" style="color: var(--text-color-secondary)"></i>
          <span class="text-color-secondary">Mobil:</span>
          <span>{{ member.mobile }}</span>
        </div>

        <div v-if="member.city" class="flex align-items-center gap-2">
          <i class="pi pi-map-marker" style="color: var(--text-color-secondary)"></i>
          <span class="text-color-secondary">Ort:</span>
          <span>{{ member.city }}</span>
        </div>
      </div>

      <Divider />

      <div class="flex gap-2 mt-3">
        <Button
          label="Ansehen"
          icon="pi pi-eye"
          outlined
          size="small"
          @click="$emit('view', member)"
          class="flex-1"
        />
        <Button
          label="Bearbeiten"
          icon="pi pi-pencil"
          severity="secondary"
          outlined
          size="small"
          @click="$emit('edit', member)"
          class="flex-1"
        />
        <Button
          icon="pi pi-trash"
          severity="danger"
          outlined
          size="small"
          @click="$emit('delete', member)"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import type { Member } from '@/types/api'

interface Props {
  member: Member
}

const props = defineProps<Props>()

defineEmits<{
  view: [member: Member]
  edit: [member: Member]
  delete: [member: Member]
}>()

const memberInitials = computed(() => {
  return `${props.member.name[0]}${props.member.lastname[0]}`.toUpperCase()
})

const formatDate = (dateString: string | null) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
</script>
