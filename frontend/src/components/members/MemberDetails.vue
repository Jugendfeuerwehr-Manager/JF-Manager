<template>
  <div v-if="member">
    <div class="flex align-items-start gap-4 mb-4">
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
        <h2 class="m-0 mb-2">{{ member.full_name }}</h2>
        <div class="flex gap-2 mb-2">
          <Tag v-if="member.status" :value="member.status.name" :style="{ backgroundColor: member.status.color }" />
          <Tag v-if="member.group" :value="`Gruppe: ${member.group.name}`" severity="secondary" />
        </div>
        <p v-if="member.age" class="m-0 text-color-secondary">{{ member.age }} Jahre alt</p>
      </div>
    </div>

    <Divider />

    <div class="grid">
      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Vorname</label>
          <p class="m-0">{{ member.name }}</p>
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Nachname</label>
          <p class="m-0">{{ member.lastname }}</p>
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Geburtstag</label>
          <p class="m-0">{{ formatDate(member.birthday) }}</p>
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Eingetreten</label>
          <p class="m-0">{{ formatDate(member.joined) }}</p>
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">E-Mail</label>
          <p class="m-0">{{ member.email || '-' }}</p>
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Telefon</label>
          <p class="m-0">{{ member.phone || '-' }}</p>
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Mobil</label>
          <p class="m-0">{{ member.mobile || '-' }}</p>
        </div>
      </div>

      <div class="col-12 md:col-6">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Ausweis Nr.</label>
          <p class="m-0">{{ member.identityCardNumber || '-' }}</p>
        </div>
      </div>

      <div class="col-12">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Adresse</label>
          <p class="m-0">
            <span v-if="member.street">{{ member.street }}<br /></span>
            <span v-if="member.zip_code || member.city">{{ member.zip_code }} {{ member.city }}</span>
            <span v-if="!member.street && !member.zip_code && !member.city">-</span>
          </p>
        </div>
      </div>

      <div class="col-12">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Kann schwimmen</label>
          <Chip :label="member.canSwimm ? 'Ja' : 'Nein'" :icon="member.canSwimm ? 'pi pi-check' : 'pi pi-times'" />
        </div>
      </div>

      <div class="col-12" v-if="member.notes">
        <div class="mb-3">
          <label class="block text-sm font-semibold mb-1">Bemerkungen</label>
          <p class="m-0">{{ member.notes }}</p>
        </div>
      </div>
    </div>

    <Divider />

    <div v-if="member">
      <h3 class="mb-3">Eltern</h3>
      <ParentContacts :member="member" variant="detailed" />
    </div>

    <div class="flex justify-content-end gap-2">
      <Button label="Schließen" severity="secondary" @click="emit('close')" />
      <Button label="Bearbeiten" icon="pi pi-pencil" @click="emit('edit')" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Member } from '@/types/api'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import ParentContacts from '@/components/members/ParentContacts.vue'

interface Props {
  member: Member | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  edit: []
}>()

const memberInitials = computed(() => {
  if (!props.member) return ''
  return `${props.member.name[0]}${props.member.lastname[0]}`.toUpperCase()
})

const formatDate = (dateString?: string | null) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
</script>
