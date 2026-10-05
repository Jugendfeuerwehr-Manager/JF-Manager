<template>
  <span class="member-identity">
    <PrivateAvatar :image="member.avatar_url" :label="member.avatar_url ? undefined : initials" shape="circle" class="member-identity__avatar" />
    <span class="member-identity__text">
      <span class="member-identity__name">{{ member.full_name }}</span>
      <span class="member-identity__meta"><slot>{{ meta }}</slot></span>
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PrivateAvatar from '@/components/common/PrivateAvatar.vue'
import type { Member } from '@/types/members'

const props = defineProps<{ member: Member }>()

const initials = computed(() => `${props.member.name?.[0] ?? ''}${props.member.lastname?.[0] ?? ''}`.toUpperCase())
const meta = computed(() => [props.member.age ? `${props.member.age} Jahre` : '', props.member.group?.name ?? ''].filter(Boolean).join(' · '))
</script>

<style scoped>
.member-identity {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  min-width: 0;
}

.member-identity__avatar {
  flex: none;
  width: 40px;
  height: 40px;
  background: var(--surface-hover);
  color: var(--p-surface-700);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-bold);
}

.app-dark .member-identity__avatar {
  color: var(--p-surface-200);
}

.member-identity__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.3;
}

.member-identity__name {
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-identity__meta {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}
</style>
