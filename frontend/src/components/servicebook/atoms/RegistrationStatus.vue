<template>
  <span class="registration-status" :class="[`registration-status--${tone}`, { 'registration-status--guest': guest }]">
    <i :class="icon" aria-hidden="true"></i>
    <span>{{ text }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RegistrationPerson } from '@/types/servicebook'
import { REGISTRATION_STATE, reasonLabel, registrationLabel } from '@/utils/registrationState'

const props = defineProps<{ person: RegistrationPerson }>()

const guest = computed(() => !props.person.in_target)
const meta = computed(() => (props.person.state ? REGISTRATION_STATE[props.person.state] : null))
const tone = computed(() => meta.value?.tone ?? 'neutral')
const icon = computed(() => (guest.value && !meta.value ? 'pi pi-user-plus' : meta.value?.icon ?? 'pi pi-circle'))
const text = computed(() => {
  const parts: string[] = []
  if (guest.value) parts.push('Gast')
  const label = props.person.state ? registrationLabel(props.person) : ''
  if (label) parts.push(label)
  const reason = reasonLabel(props.person.reason_category)
  if (props.person.state === 'cancelled' && reason) parts.push(reason)
  return parts.join(' · ') || 'erwartet'
})
</script>

<style scoped>
.registration-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
  overflow-wrap: anywhere;
}
.registration-status i { font-size: 0.8rem; flex: none; }
.registration-status--bad { color: var(--p-red-800); font-weight: var(--jf-weight-semibold); }
.registration-status--ok { color: var(--p-green-800); }
.registration-status--warn { color: var(--p-amber-900); }
.app-dark .registration-status--bad { color: var(--p-red-300); }
.app-dark .registration-status--ok { color: var(--p-green-300); }
.app-dark .registration-status--warn { color: var(--p-amber-300); }
</style>
