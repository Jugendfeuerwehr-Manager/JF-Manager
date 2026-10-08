<template>
  <section aria-label="Freigaben" class="releases">
    <StateView v-if="store.policyLoading && !overview" kind="loading" />
    <StateView v-else-if="store.policyError && !overview" kind="error" :message="store.policyError" @retry="store.loadPolicies()" />
    <template v-else-if="overview && draft">
      <div class="scope">
        <label for="release-scope" class="scope__label">Geltungsbereich</label>
        <!-- Searchable: organisations may have a hundred departments. -->
        <Select
          input-id="release-scope"
          :model-value="scopeValue"
          :options="scopeGroups"
          option-group-label="label"
          option-group-children="items"
          option-label="label"
          option-value="value"
          filter
          filter-placeholder="Abteilung suchen …"
          empty-filter-message="Keine Abteilung gefunden"
          class="scope__select"
          @update:model-value="onScope"
        >
          <template #option="{ option }">
            <span class="scope__option">
              <span>{{ option.label }}</span>
              <span v-if="option.deviates" class="scope__badge"><i class="pi pi-sliders-h" aria-hidden="true" />weicht ab</span>
            </span>
          </template>
        </Select>
        <span v-if="deviating > 0" class="muted small">{{ deviating }} {{ deviating === 1 ? 'Abteilung weicht' : 'Abteilungen weichen' }} von den Vorgaben ab.</span>
      </div>

      <Message v-if="store.policyNotice" :severity="store.policyNotice.severity" :closable="false" role="status">{{ store.policyNotice.text }}</Message>
      <Message v-if="!editable" severity="info" :closable="false">Du kannst die Freigaben einsehen, aber nicht ändern.</Message>

      <div class="card">
        <h2>Eigene Konten für Mitglieder</h2>
        <p class="muted small">Legt fest, ab wann Mitglieder selbst ein Portalkonto bekommen können.{{ scopeIsOrg ? ' Abteilungen übernehmen diese Vorgabe, wenn sie nichts anderes einstellen.' : '' }}</p>
        <fieldset class="modes" :disabled="!editable || store.policySaving">
          <legend class="sr-only">Mitgliederkonten</legend>
          <label v-for="option in modeOptions" :key="option.value" class="mode">
            <input type="radio" name="member-portal-mode" :value="option.value" :checked="draft.mode === option.value" @change="store.editMode(option.value)" />
            <span v-if="option.value !== 'min_age'">{{ option.label }}</span>
            <span v-else class="age">
              Ab einem Alter von
              <input type="number" min="0" max="99" inputmode="numeric" class="age__input" aria-label="Mindestalter in Jahren" :value="draft.minAge ?? ''" :disabled="draft.mode !== 'min_age' || !editable" :aria-invalid="!!errors.member_portal_min_age" @input="onAge" />
              Jahren
            </span>
          </label>
        </fieldset>
        <p v-if="errors.member_portal_min_age" class="error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i> {{ errors.member_portal_min_age }}</p>
        <p v-if="errors.member_portal_mode" class="error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i> {{ errors.member_portal_mode }}</p>
        <p v-if="stats" class="stats">
          Betrifft {{ stats.eligible }} {{ stats.eligible === 1 ? 'Mitglied' : 'Mitglieder' }} in {{ department?.name }}.
          Ohne hinterlegtes Geburtsdatum ist keine Einladung möglich ({{ stats.missing_birthday }} {{ stats.missing_birthday === 1 ? 'Mitglied' : 'Mitglieder' }}).
        </p>
      </div>

      <div class="card">
        <h2>Was Eltern und Mitglieder sehen</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th scope="col">Kategorie</th><th scope="col">Eltern</th><th scope="col">Mitglieder</th></tr>
            </thead>
            <tbody>
              <tr v-for="category in overview.categories" :key="category.key">
                <th scope="row">
                  <span class="cat">{{ category.label }}</span>
                  <span class="muted small">{{ category.hint }}</span>
                </th>
                <td v-for="audience in audiences" :key="audience.value" :data-cell="`${category.key}.${audience.value}`">
                  <span v-if="!category.audiences.includes(audience.value)" class="muted" aria-label="nicht zutreffend">–</span>
                  <span v-else-if="category.fixed" class="fixed"><i class="pi pi-check" aria-hidden="true"></i> immer</span>
                  <span v-else-if="isLocked(category.key, audience.value)" class="locked">
                    <i class="pi pi-lock" aria-hidden="true"></i> gesperrt
                    <span class="muted small">({{ labelOf(effective(category.key, audience.value)) }})</span>
                  </span>
                  <template v-else>
                    <span v-if="!editable" class="readonly">{{ readonlyText(category.key, audience.value) }}</span>
                    <template v-else>
                      <SegmentedControl
                        :model-value="cellValue(category.key, audience.value)"
                        :options="cellOptions(category.key, audience.value)"
                        :label="`${category.label} für ${audience.label}`"
                        class="cell"
                        @update:model-value="(v: string) => onCell(category.key, audience.value, v)"
                      />
                      <label v-if="scopeIsOrg" class="lock">
                        <input type="checkbox" :checked="draft.ceiling[category.key]?.[audience.value] === 'locked'" @change="(e) => store.editCeiling(category.key, audience.value, (e.target as HTMLInputElement).checked ? 'locked' : 'allowed')" />
                        für Abteilungen sperren
                      </label>
                    </template>
                  </template>
                  <p v-if="errors[`${category.key}.${audience.value}`]" class="error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i> {{ errors[`${category.key}.${audience.value}`] }}</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="note"><i class="pi pi-lock" aria-hidden="true"></i> {{ overview.never_visible }}</p>
      </div>

      <div v-if="editable" class="actions">
        <Button label="Verwerfen" severity="secondary" outlined :disabled="!store.policyDirty || store.policySaving" @click="store.discardPolicy()" />
        <Button label="Speichern" icon="pi pi-check" :disabled="!store.policyDirty" :loading="store.policySaving" @click="save" />
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Select from 'primevue/select'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import StateView from '@/components/common/StateView.vue'
import type { Audience, MemberPortalMode, Visibility } from '@/api/portalAdmin'
import { usePortalAdminStore } from '@/stores/portalAdmin'

const store = usePortalAdminStore()
const overview = computed(() => store.overview)
const draft = computed(() => store.policyDraft)
const errors = computed(() => store.policyErrors)
const scopeIsOrg = computed(() => store.policyScope === 'org')
const scopeValue = computed(() => String(store.policyScope))
const department = computed(() => (store.policyScope === 'org' ? null : overview.value?.departments.find(d => d.id === store.policyScope) ?? null))
const editable = computed(() => (scopeIsOrg.value ? overview.value?.organization.editable : department.value?.editable) ?? false)
const stats = computed(() => (department.value?.member_portal.mode === 'min_age' ? department.value.member_portal : null))

const audiences: { value: Audience, label: string }[] = [{ value: 'parents', label: 'Eltern' }, { value: 'members', label: 'Mitglieder' }]
const deviates = (d: { overrides: Record<string, unknown>, member_portal_mode: string }) =>
  Object.keys(d.overrides ?? {}).length > 0 || !!d.member_portal_mode
const scopeGroups = computed(() => [
  { label: 'Organisation', items: [{ value: 'org', label: 'Organisation (Vorgaben)', deviates: false }] },
  {
    label: 'Abteilungen',
    items: (overview.value?.departments ?? []).map(d => ({ value: String(d.id), label: d.name, deviates: deviates(d) })),
  },
])
const deviating = computed(() => (overview.value?.departments ?? []).filter(deviates).length)
const modeOptions = computed<{ value: '' | MemberPortalMode, label: string }[]>(() => [
  ...(scopeIsOrg.value ? [] : [{ value: '' as const, label: 'Wie Organisation' }]),
  { value: 'off', label: 'Keine Mitgliederkonten' },
  { value: 'min_age', label: 'Ab einem Alter von' },
  { value: 'all', label: 'Für alle Mitglieder' },
])

const labelOf = (v: Visibility | undefined) => (v === 'visible' ? 'sichtbar' : 'verborgen')
const effective = (cat: string, aud: Audience) => (scopeIsOrg.value
  ? overview.value?.organization.effective[cat]?.[aud]
  : department.value?.effective[cat]?.[aud])
const isLocked = (cat: string, aud: Audience) => !scopeIsOrg.value && !!department.value?.locked[cat]?.[aud]
const cellValue = (cat: string, aud: Audience) => draft.value?.visibility[cat]?.[aud] ?? ''
const readonlyText = (cat: string, aud: Audience) => {
  const inherited = !scopeIsOrg.value && !department.value?.overrides[cat]?.[aud]
  return `${labelOf(effective(cat, aud))}${inherited ? ' (wie Organisation)' : ''}`
}
function cellOptions(cat: string, aud: Audience) {
  const options = [{ value: 'visible', label: 'sichtbar' }, { value: 'hidden', label: 'verborgen' }]
  if (scopeIsOrg.value) return options
  const orgValue = overview.value?.organization.effective[cat]?.[aud]
  return [{ value: '', label: `Wie Organisation (${labelOf(orgValue)})` }, ...options]
}
function onCell(cat: string, aud: Audience, value: string) { store.editVisibility(cat, aud, value as Visibility | '') }
function onAge(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  store.editMinAge(raw === '' ? null : Number(raw))
}
function onScope(value: string) { store.setPolicyScope(value === 'org' ? 'org' : Number(value)) }
async function save() { await store.savePolicy() }

onMounted(() => { if (!store.overview) void store.loadPolicies() })
</script>

<style scoped>
.releases { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.scope { display: flex; flex-direction: column; gap: var(--jf-space-0-5); max-width: 32rem; }
.scope__label { font-weight: var(--jf-weight-semibold); font-size: var(--jf-text-sm); }
.scope__select { width: 100%; min-height: var(--jf-touch-target); }
.scope__option { display: flex; align-items: center; justify-content: space-between; gap: var(--jf-space-1); width: 100%; }
.scope__badge { display: inline-flex; align-items: center; gap: var(--jf-space-0-5); font-size: var(--jf-text-xs, 0.75rem); color: var(--jf-color-text-muted); }
.card { display: flex; flex-direction: column; gap: var(--jf-space-1-5); padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
h2 { margin: 0; font-size: var(--jf-text-lg, 1.125rem); font-weight: var(--jf-weight-semibold); }
p { margin: 0; }
.muted { color: var(--jf-color-text-muted); }
.small { font-size: var(--jf-text-sm); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.modes { display: flex; flex-direction: column; gap: var(--jf-space-0-5); margin: 0; padding: 0; border: 0; }
.mode { display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); }
.mode input[type='radio'] { width: 1.25rem; height: 1.25rem; }
.age { display: inline-flex; align-items: center; gap: var(--jf-space-1); }
.age__input { width: 4.5rem; min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1); border: 1px solid var(--p-form-field-border-color); border-radius: var(--jf-radius-md); background: var(--p-form-field-background); color: var(--jf-color-text); font: inherit; }
.age__input:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.stats { padding: var(--jf-space-1) var(--jf-space-1-5); border-radius: var(--jf-radius-md); background: var(--jf-color-ground); color: var(--jf-color-text); font-size: var(--jf-text-sm); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: var(--jf-space-1-5) var(--jf-space-1); border-bottom: 1px solid var(--jf-color-border); text-align: left; vertical-align: top; }
thead th { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); font-weight: var(--jf-weight-semibold); }
tbody th { font-weight: normal; min-width: 11rem; }
.cat { display: block; font-weight: var(--jf-weight-semibold); }
.cell { min-width: 11rem; }
.fixed, .locked { display: inline-flex; align-items: center; gap: var(--jf-space-0-5); min-height: var(--jf-touch-target); }
.lock { display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); font-size: var(--jf-text-sm); }
.error { display: flex; gap: var(--jf-space-0-5); align-items: center; color: var(--p-red-700); font-size: var(--jf-text-sm); }
.app-dark .error { color: var(--p-red-300); }
.note { display: flex; gap: var(--jf-space-1); align-items: flex-start; color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.actions { display: flex; justify-content: flex-end; gap: var(--jf-space-1-5); }
.actions :deep(.p-button) { min-height: var(--jf-touch-target); }
</style>
