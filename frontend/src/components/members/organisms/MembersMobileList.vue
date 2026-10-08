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
      <div class="member-row">
        <button type="button" class="member-row__main" :aria-label="`${member.full_name} öffnen`" @click="emit('view', member)">
          <MemberIdentity :member="member">
            <span>{{ metaFor(member) }}</span>
            <MemberStatusBadge :status="member.status" />
          </MemberIdentity>
        </button>
        <a
          v-if="contactFor(member)"
          class="member-row__call"
          :href="`tel:${contactFor(member)!.number}`"
          :aria-label="`${contactFor(member)!.name} anrufen (Kontakt von ${member.full_name})`"
        >
          <i class="pi pi-phone" aria-hidden="true"></i>
        </a>
      </div>
    </template>
    <template #empty>
      <StateView kind="empty" title="Keine Mitglieder gefunden" message="Passe Suche oder Filter an oder lege einen neuen Eintrag an." />
    </template>
  </ResponsiveList>
</template>

<script setup lang="ts">
import StateView from '@/components/common/StateView.vue'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import MemberIdentity from '@/components/members/atoms/MemberIdentity.vue'
import MemberStatusBadge from '@/components/members/atoms/MemberStatusBadge.vue'
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

function metaFor(member: Member) {
  return [member.age ? `${member.age} J.` : '', member.group?.name ?? ''].filter(Boolean).join(' · ')
}

/** First parent with a phone number; members without one get no call button. */
function contactFor(member: Member) {
  for (const parent of member.parents ?? []) {
    const number = parent.mobile || parent.phone
    if (number) return { name: parent.full_name, number }
  }
  return null
}
</script>

<style scoped>
.member-row {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding-right: var(--jf-space-0-5);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
}

.member-row__main {
  flex: 1;
  min-width: 0;
  min-height: 64px;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 0;
  border-radius: var(--jf-radius-lg);
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.member-row__main:active {
  background: var(--surface-hover);
}

.member-row__call {
  display: inline-grid;
  place-items: center;
  flex: none;
  width: var(--jf-touch-target);
  height: var(--jf-touch-target);
  border-radius: 999px;
  color: var(--jf-color-primary);
  text-decoration: none;
}

.member-row__call:hover {
  background: var(--jf-color-selected);
}
</style>
