<template>
  <section class="registrations" aria-label="Meldungen">
    <StateView v-if="loading && !data" kind="loading" title="Meldungen werden geladen …" />
    <StateView v-else-if="error && !data" :kind="stateForError(error)" title="Meldungen konnten nicht geladen werden" @retry="$emit('retry')" />
    <template v-else-if="data">
      <StateView
        v-if="!data.session"
        kind="empty"
        title="Keine Anmeldung für diesen Dienst"
        message="Für diesen Dienst ist keine Teilnahmemeldung eingerichtet. Die Anwesenheit kann trotzdem erfasst werden."
      />
      <template v-else>
        <dl class="counters" aria-label="Zähler">
          <div class="counter"><dt>erwartet</dt><dd>{{ data.counts.expected }}</dd></div>
          <div class="counter"><dt>abgemeldet</dt><dd>{{ data.counts.cancelled }}</dd></div>
          <div v-if="data.counts.registered" class="counter"><dt>angemeldet</dt><dd>{{ data.counts.registered }}</dd></div>
          <div v-if="data.counts.waitlisted" class="counter"><dt>Warteliste</dt><dd>{{ data.counts.waitlisted }}</dd></div>
          <div class="counter"><dt>keine Rückmeldung</dt><dd>{{ data.counts.no_response }}</dd></div>
          <div v-if="data.counts.guests" class="counter"><dt>Gäste</dt><dd>{{ data.counts.guests }}</dd></div>
          <div v-if="data.counts.conflicts" class="counter counter--warn"><dt>Konflikte</dt><dd>{{ data.counts.conflicts }}</dd></div>
        </dl>

        <section v-for="group in groups" :key="group.key" class="group" :aria-labelledby="`reg-${group.key}`">
          <h3 :id="`reg-${group.key}`" class="group__title">{{ group.title }} ({{ group.people.length }})</h3>
          <ul class="group__list">
            <li v-for="person in group.people" :key="person.member_id" class="reg-row">
              <div class="reg-row__main">
                <span class="reg-row__name">{{ person.name }}</span>
                <RegistrationStatus :person="person" />
                <span v-if="detail(person)" class="reg-row__detail">{{ detail(person) }}</span>
              </div>
              <button
                v-if="person.reason_note"
                type="button"
                class="reg-row__toggle"
                :aria-expanded="isOpen(person)"
                :aria-controls="`note-${person.member_id}`"
                @click="toggle(person)"
              >
                <i :class="isOpen(person) ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" aria-hidden="true"></i>
                {{ isOpen(person) ? 'Nachricht ausblenden' : 'Nachricht anzeigen' }}
              </button>
              <p v-if="person.reason_note && isOpen(person)" :id="`note-${person.member_id}`" class="reg-row__note">{{ person.reason_note }}</p>
            </li>
          </ul>
        </section>
        <p v-if="!groups.length" class="empty">Noch keine Meldungen.</p>
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import RegistrationStatus from '../atoms/RegistrationStatus.vue'
import type { RegistrationPerson, ServiceRegistrations } from '@/types/servicebook'
import type { ApiErrorKind } from '@/utils/apiError'
import { formatDateTime, sourceLabel } from '@/utils/registrationState'

const props = defineProps<{ data: ServiceRegistrations | null; loading?: boolean; error?: ApiErrorKind | null }>()
defineEmits<{ retry: [] }>()

const opened = ref(new Set<number>())
const isOpen = (p: RegistrationPerson) => opened.value.has(p.member_id)
function toggle(p: RegistrationPerson) {
  const next = new Set(opened.value)
  if (!next.delete(p.member_id)) next.add(p.member_id)
  opened.value = next
}

function detail(p: RegistrationPerson) {
  const parts = [sourceLabel(p.source), formatDateTime(p.at)].filter(Boolean)
  if (p.late) parts.push('nach Frist')
  return parts.join(' · ')
}

const groups = computed(() => {
  const people = props.data?.people ?? []
  const defs: Array<{ key: string; title: string; match: (p: RegistrationPerson) => boolean }> = [
    { key: 'cancelled', title: 'Abgemeldet', match: (p) => p.state === 'cancelled' },
    { key: 'registered', title: 'Angemeldet', match: (p) => ['registered', 'applied', 'assigned', 'not_selected'].includes(p.state ?? '') },
    { key: 'waitlisted', title: 'Warteliste', match: (p) => p.state === 'waitlisted' },
    { key: 'expected', title: 'Erwartet ohne Meldung', match: (p) => p.state === 'expected' },
    { key: 'pending', title: 'Keine Rückmeldung', match: (p) => p.state === 'no_response' },
  ]
  return defs
    .map((d) => ({ key: d.key, title: d.title, people: people.filter(d.match) }))
    .filter((g) => g.people.length)
})
</script>

<style scoped>
.registrations { display: flex; flex-direction: column; gap: var(--jf-space-2); min-width: 0; }
.counters { display: grid; grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr)); gap: var(--jf-space-1); margin: 0; }
.counter {
  display: flex;
  flex-direction: column-reverse;
  padding: var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
}
.counter dt { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.counter dd { margin: 0; font-size: var(--jf-text-xl); font-weight: var(--jf-weight-bold); }
.counter--warn dd { color: var(--p-amber-900); }
.app-dark .counter--warn dd { color: var(--p-amber-300); }
.group__title { margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-sm); font-weight: var(--jf-weight-bold); letter-spacing: 0.04em; text-transform: uppercase; color: var(--jf-color-text-muted); }
.group__list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: var(--jf-space-1); }
.reg-row { display: flex; flex-direction: column; gap: var(--jf-space-0-5); padding: var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
.reg-row__main { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--jf-space-0-5) var(--jf-space-1-5); }
.reg-row__name { font-weight: var(--jf-weight-semibold); overflow-wrap: anywhere; }
.reg-row__detail { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.reg-row__toggle { align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; min-height: var(--jf-touch-target); padding: 0; border: 0; background: transparent; color: var(--jf-color-primary); font: inherit; font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); cursor: pointer; }
.reg-row__note { margin: 0; padding: var(--jf-space-1) var(--jf-space-1-5); border-radius: var(--jf-radius-md); background: var(--surface-hover); overflow-wrap: anywhere; }
.empty { margin: 0; color: var(--jf-color-text-muted); }
@media (min-width: 768px) {
  .group__list { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); }
}
</style>
