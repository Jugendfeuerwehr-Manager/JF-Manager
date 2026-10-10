<template>
  <div class="own-data">
    <StateView v-if="portal.personLoading" kind="loading" title="Daten werden geladen …" />
    <StateView v-else-if="portal.personError" kind="error" :message="portal.personError.message" @retry="portal.loadPerson(portal.selectedPersonId)" />
    <template v-else-if="data">
      <section class="card" aria-labelledby="own-contact">
        <div class="card-head">
          <h2 id="own-contact">Name und Kontakt</h2>
          <router-link v-if="editLink" :to="editLink" class="edit-link"><i class="pi pi-pencil" aria-hidden="true"></i>Bearbeiten</router-link>
        </div>
        <dl>
          <div v-for="row in contactRows" :key="row.label">
            <dt>{{ row.label }}</dt>
            <dd><ContactLink v-if="row.kind" :kind="row.kind" :value="row.value" /><span v-else>{{ row.value || '–' }}</span></dd>
          </div>
        </dl>
        <p class="muted">
          {{ editLink || relation === 'child' ? 'Änderungen an eigenen Datensätzen werden als „Eigenänderung“ im Verlauf protokolliert.' : 'Für Änderungen fehlt dir das Recht in dieser Abteilung; wende dich an die Leitung.' }}
        </p>
      </section>

      <section v-if="data.group" class="card" aria-labelledby="own-group">
        <h2 id="own-group">Gruppe und Abteilung</h2>
        <p>{{ [data.group.group, data.group.departments.join(', ')].filter(Boolean).join(' · ') || '–' }}</p>
      </section>

      <section class="card" aria-labelledby="own-evidence">
        <h2 id="own-evidence">Qualifikationen</h2>
        <ul v-if="qualifications.length" class="list">
          <li v-for="(q, i) in qualifications" :key="i">
            <span class="item-title">{{ q.type }}</span>
            <span class="muted">{{ q.source }}<template v-if="q.expires"> · gültig bis {{ day(q.expires) }}</template></span>
            <StatusBadge v-if="!q.valid" label="Abgelaufen" severity="danger" />
          </li>
        </ul>
        <p v-else class="muted">Keine Qualifikationen eingetragen.</p>
        <template v-if="data.special_tasks">
          <h3>Sonderaufgaben</h3>
          <ul v-if="data.special_tasks.length" class="list">
            <li v-for="(t, i) in data.special_tasks" :key="i"><span class="item-title">{{ t.task }}</span><span v-if="t.start" class="muted">seit {{ day(t.start) }}<template v-if="t.end"> bis {{ day(t.end) }}</template></span></li>
          </ul>
          <p v-else class="muted">Keine Sonderaufgaben eingetragen.</p>
        </template>
        <p class="lock" role="note"><i class="pi pi-lock" aria-hidden="true"></i>{{ notice }}</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ContactLink from '@/components/common/ContactLink.vue'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { usePortalStore } from '@/stores/portal'

const props = defineProps<{ relation: 'self' | 'child' }>()
const portal = usePortalStore()
const data = computed(() => portal.personData)

const notice = computed(() => portal.me?.evidence_notice ?? 'Nachweise pflegt eine andere Person.')
// Own master data is edited directly with the existing rights (E14); children through the member module.
const editLink = computed(() => (data.value && props.relation === 'self' && portal.me?.can_edit?.member ? `/members/${data.value.id}/edit` : null))

const dateFormat = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
function day(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`)
  return Number.isNaN(d.getTime()) ? iso : dateFormat.format(d)
}

interface Row { label: string, value: string, kind?: 'phone' | 'email' }
const contactRows = computed<Row[]>(() => {
  const c = data.value?.contact
  if (!c) return []
  return [
    { label: 'Name', value: `${c.first_name} ${c.last_name}`.trim() },
    ...(data.value?.birthday ? [{ label: 'Geburtstag', value: day(data.value.birthday) }] : []),
    { label: 'Adresse', value: [c.street, [c.zip_code, c.city].filter(Boolean).join(' ')].filter(Boolean).join(', ') },
    { label: 'Telefon', value: c.phone, kind: 'phone' as const },
    { label: 'Mobil', value: c.mobile, kind: 'phone' as const },
    { label: 'E-Mail', value: c.email, kind: 'email' as const },
  ]
})

const qualifications = computed(() => [
  ...(data.value?.qualifications ?? []).map(q => ({ ...q, source: 'am Mitglied' })),
  ...(data.value?.account_qualifications ?? []).map(q => ({ ...q, source: 'am Konto' })),
])
</script>

<style scoped>
.own-data { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.card { display: flex; flex-direction: column; gap: var(--jf-space-1-5); padding: var(--jf-space-2); background: var(--jf-color-card); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: var(--jf-space-1); }
h2 { margin: 0; font-size: var(--jf-text-md); font-weight: var(--jf-weight-semibold); }
h3 { margin: var(--jf-space-1) 0 0; font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); }
p { margin: 0; }
dl { margin: 0; display: flex; flex-direction: column; gap: var(--jf-space-1); }
dl > div { display: flex; justify-content: space-between; gap: var(--jf-space-1-5); }
dt { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
dd { margin: 0; text-align: right; overflow-wrap: anywhere; }
.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--jf-space-1); }
.list li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-0-5) var(--jf-space-1-5); }
.item-title { font-weight: var(--jf-weight-semibold); }
.muted { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.lock { display: flex; gap: var(--jf-space-1); align-items: flex-start; padding: var(--jf-space-1) var(--jf-space-1-5); border-radius: var(--jf-radius-md); background: var(--surface-hover); font-size: var(--jf-text-sm); }
.edit-link { display: inline-flex; align-items: center; gap: var(--jf-space-0-5); min-height: var(--jf-touch-target); color: var(--jf-color-primary); font-weight: var(--jf-weight-semibold); font-size: var(--jf-text-sm); text-decoration: none; }
.edit-link:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
</style>
