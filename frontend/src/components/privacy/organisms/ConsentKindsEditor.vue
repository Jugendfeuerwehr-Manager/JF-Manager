<template>
  <div class="consent-kinds">
    <div class="consent-kinds__header">
      <p class="consent-kinds__intro">
        Welche Einwilligungen ihr erfasst. Arten „im Portal“ erteilen und widerrufen Eltern selbst für jedes Kind.
        Eine Änderung am Wortlaut erhöht die Version; bestehende Einwilligungen behalten die Version, zu der sie erteilt wurden.
      </p>
      <Button v-if="canEdit && !form" label="Neue Einwilligungsart" icon="pi pi-plus" size="small" @click="openForm()" />
    </div>

    <Message v-if="privacyStore.kindsError" severity="error" :closable="false">{{ privacyStore.kindsError }}</Message>

    <form v-if="form" class="consent-kinds__form" novalidate @submit.prevent="save">
      <h3>{{ editingId ? 'Einwilligungsart bearbeiten' : 'Neue Einwilligungsart' }}</h3>
      <div class="consent-kinds__grid">
        <div class="field">
          <label for="kind-label">Bezeichnung</label>
          <InputText id="kind-label" v-model="form.label" maxlength="200" @input="suggestSlug" />
        </div>
        <div class="field">
          <label for="kind-slug">Kennung</label>
          <InputText id="kind-slug" v-model="form.slug" maxlength="50" :disabled="!!editingId" aria-describedby="kind-slug-hint" />
          <small id="kind-slug-hint">Technischer Name, nach dem Anlegen fest.</small>
        </div>
      </div>
      <div class="field">
        <label for="kind-description">Wortlaut</label>
        <Textarea id="kind-description" v-model="form.description" rows="4" auto-resize aria-describedby="kind-description-hint" />
        <small id="kind-description-hint">Das sehen Eltern im Portal und es wird mit jeder Einwilligung gespeichert.</small>
      </div>
      <div class="consent-kinds__switches">
        <label class="switch"><ToggleSwitch v-model="form.in_portal" input-id="kind-portal" /> Im Portal anbieten</label>
        <label class="switch"><ToggleSwitch v-model="form.active" input-id="kind-active" /> Aktiv</label>
      </div>
      <div class="consent-kinds__form-actions">
        <Button type="button" label="Abbrechen" severity="secondary" text @click="form = null" />
        <Button type="submit" label="Speichern" icon="pi pi-check" :disabled="!form.label || !form.slug" :loading="privacyStore.kindsSaving" />
      </div>
    </form>

    <ul class="consent-kinds__list">
      <li v-for="kind in privacyStore.consentKinds" :key="kind.id" :class="{ 'is-inactive': !kind.active }">
        <div class="consent-kinds__text">
          <span class="consent-kinds__label">{{ kind.label }}</span>
          <span class="consent-kinds__meta">
            {{ kind.slug }} · Version {{ kind.version }}
            <span v-if="kind.in_portal" class="tag tag--portal">Im Portal</span>
            <span v-if="kind.built_in" class="tag">Mitgeliefert</span>
            <span v-if="!kind.active" class="tag">Inaktiv</span>
          </span>
        </div>
        <div v-if="canEdit" class="consent-kinds__actions">
          <Button icon="pi pi-pencil" text severity="secondary" :aria-label="`${kind.label} bearbeiten`" @click="openForm(kind)" />
          <Button
            v-if="!kind.built_in"
            icon="pi pi-trash"
            text
            severity="danger"
            :aria-label="`${kind.label} löschen`"
            v-tooltip.top="'Nur ungenutzte Arten lassen sich löschen, sonst deaktivieren'"
            @click="privacyStore.deleteConsentKind(kind.id)"
          />
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { usePrivacyStore } from '@/stores/privacy'
import type { ConsentKind, ConsentKindInput } from '@/types/privacy'

interface Props {
  canEdit: boolean
}

defineProps<Props>()
const privacyStore = usePrivacyStore()
const form = ref<ConsentKindInput | null>(null)
const editingId = ref<number | null>(null)

onMounted(() => { void privacyStore.fetchConsentKinds() })

function openForm(kind?: ConsentKind) {
  editingId.value = kind?.id ?? null
  form.value = kind
    ? { slug: kind.slug, label: kind.label, description: kind.description, in_portal: kind.in_portal, active: kind.active, position: kind.position }
    : { slug: '', label: '', description: '', in_portal: true, active: true, position: privacyStore.consentKinds.length }
}

/** New kinds get a slug from their label until someone edits it. */
function suggestSlug() {
  if (!form.value || editingId.value) return
  form.value.slug = form.value.label
    .toLowerCase()
    .replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 50)
}

async function save() {
  if (!form.value) return
  const data = editingId.value ? { ...form.value, slug: undefined } : form.value
  if (await privacyStore.saveConsentKind(data as ConsentKindInput, editingId.value ?? undefined)) form.value = null
}
</script>

<style scoped>
.consent-kinds { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.consent-kinds__header { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: var(--jf-space-1); }
.consent-kinds__intro { margin: 0; flex: 1 1 24rem; font-size: 0.875rem; color: var(--jf-color-text-muted); }
.consent-kinds__form {
  display: flex; flex-direction: column; gap: var(--jf-space-1-5);
  padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md);
}
.consent-kinds__form h3 { margin: 0; font-size: 1rem; }
.consent-kinds__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: var(--jf-space-1-5); }
.field { display: flex; flex-direction: column; gap: var(--jf-space-0-5); }
.field label { font-weight: var(--jf-weight-semibold); }
.field small { color: var(--jf-color-text-muted); }
.consent-kinds__switches { display: flex; flex-wrap: wrap; gap: var(--jf-space-2); }
.switch { display: inline-flex; align-items: center; gap: var(--jf-space-1); }
.consent-kinds__form-actions { display: flex; justify-content: flex-end; gap: var(--jf-space-1); }
.consent-kinds__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.consent-kinds__list li {
  display: flex; align-items: center; justify-content: space-between; gap: var(--jf-space-1);
  padding: var(--jf-space-1) 0; border-top: 1px solid var(--jf-color-border);
}
.consent-kinds__list li.is-inactive .consent-kinds__label { color: var(--jf-color-text-muted); }
.consent-kinds__text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.consent-kinds__label { font-weight: var(--jf-weight-semibold); }
.consent-kinds__meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 0.8125rem; color: var(--jf-color-text-muted); }
.tag { padding: 0 6px; border-radius: 999px; border: 1px solid var(--jf-color-border); font-size: 0.75rem; }
.tag--portal { color: var(--jf-color-primary); border-color: var(--jf-color-primary); }
.consent-kinds__actions { display: flex; flex: none; }
</style>
