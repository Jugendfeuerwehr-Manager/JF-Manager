<template>
  <section class="configuration-section">
    <router-link to="/settings">← Einstellungen</router-link>
    <h2>{{ category?.label || 'Einstellungen' }}</h2>
    <p v-if="kind === 'training'">
      Standardwerte für neue Übungen und Bausteine. Bereits geplante Übungen bleiben erhalten.
    </p>
    <p v-if="kind === 'vocabulary'">
      Passe die Modulnamen in der Navigation an deine Organisation an.
    </p>
    <p v-if="kind === 'login'">
      Texte der öffentlichen Anmeldeseite. Nur reiner Text, Zeilenumbrüche bleiben erhalten; ein
      leeres Feld blendet den Text aus.
    </p>
    <p v-if="kind === 'security'">
      Die nächste Sitzungsprüfung verwendet die neuen Werte, auch für bereits angemeldete Geräte.
      Die maximale Dauer muss mindestens der Zeit ohne Aktivität entsprechen.
    </p>
    <p v-if="kind === 'push'">
      Richte zuerst den Versandschlüssel ein und aktiviere anschließend Push. Jedes Gerät meldet
      sich zusätzlich im persönlichen Profil an.
    </p>
    <p v-if="loading" role="status">Einstellungen werden geladen …</p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Button v-if="error && !category" label="Erneut laden" @click="load" />
    <Message v-if="success" severity="success" :closable="false">{{ success }}</Message>
    <form v-if="category" @submit.prevent="save">
      <div v-for="[name, field] in visibleFields" :key="name" class="configuration-field">
        <label :for="`config-${name}`">{{
          kind === 'security' ? field.label.replace(' (Sekunden)', '') : field.label
        }}</label>
        <input
          v-if="field.type === 'boolean'"
          :id="`config-${name}`"
          v-model="form[name]"
          type="checkbox"
          :disabled="!category.can_change || field.locked || saving"
        />
        <template v-else-if="kind === 'security'">
          <div class="duration-input">
            <input
              :id="`config-${name}`"
              type="number"
              :value="Number(form[name]) / unitSeconds(name)"
              step="any"
              :min="field.min == null ? undefined : field.min / unitSeconds(name)"
              :max="field.max == null ? undefined : field.max / unitSeconds(name)"
              :disabled="!category.can_change || field.locked || saving"
              @input="
                form[name] = Number(($event.target as HTMLInputElement).value) * unitSeconds(name)
              "
            />
            <select v-model="units[name]" :aria-label="`Einheit für ${field.label}`">
              <option value="minutes">Minuten</option>
              <option value="hours">Stunden</option>
              <option value="days">Tage</option>
            </select>
          </div>
        </template>
        <textarea
          v-else-if="field.multiline"
          :id="`config-${name}`"
          v-model="form[name] as string"
          rows="3"
          :maxlength="field.max_length"
          :disabled="!category.can_change || field.locked || saving"
        />
        <input
          v-else
          :id="`config-${name}`"
          v-model="form[name]"
          :type="
            field.secret
              ? 'password'
              : field.type === 'integer'
                ? 'number'
                : field.type === 'time'
                  ? 'time'
                  : 'text'
          "
          :min="field.min"
          :max="field.max"
          :maxlength="field.max_length"
          :autocomplete="field.secret ? 'new-password' : 'off'"
          :disabled="!category.can_change || field.locked || saving"
        />
        <small
          >{{ sourceLabel(field.source)
          }}<template v-if="field.locked"> · Am Host vorgegeben; hier gesperrt</template> ·
          {{ effectiveLabel(field.effective) }}</small
        >
        <small v-if="field.secret"
          >Leer lassen erhält den vorhandenen Wert. Geheimnisse werden nicht zurückgegeben.</small
        >
      </div>
      <template v-if="kind === 'push'">
        <p>
          {{
            values.has_private_key
              ? 'Ein privater Versandschlüssel ist hinterlegt.'
              : 'Es ist noch kein privater Versandschlüssel hinterlegt.'
          }}
        </p>
        <Button
          v-if="category.can_change && !values.has_private_key && !category.fields.subject?.locked"
          type="button"
          label="Versandschlüssel sicher erzeugen"
          :disabled="saving || !form.subject"
          @click="generateKeys"
        />
        <p v-if="!values.has_private_key && !category.fields.subject?.locked">
          Kontaktadresse für die Erzeugung: beispielsweise mailto:admin@example.org. Der Schlüssel
          wird verschlüsselt gespeichert; Push bleibt zunächst ausgeschaltet.
        </p>
        <details
          v-if="
            values.has_private_key && category.can_change && !category.fields.private_key?.locked
          "
        >
          <summary>Vorhandene Schlüssel entfernen</summary>
          <p>
            Push wird ausgeschaltet. Die bestehenden Schlüssel gehen verloren; nach neuer Erzeugung
            müssen sich alle Geräte erneut anmelden.
          </p>
          <label
            ><input v-model="confirmKeyRemoval" type="checkbox" :disabled="saving" /> Ich bestätige
            die Entfernung und die erneute Geräteanmeldung.</label
          >
          <Button
            type="button"
            label="Push ausschalten und Schlüssel entfernen"
            severity="danger"
            outlined
            :disabled="saving || !confirmKeyRemoval"
            @click="removeKeys"
          />
        </details>
        <details>
          <summary>Schlüssel manuell eintragen oder ersetzen</summary>
          <p>
            Bei einem neuen Schlüsselpaar müssen sich alle Geräte erneut anmelden. Vorhandene
            Schlüssel werden durch die automatische Erzeugung nicht ersetzt.
          </p>
          <div
            v-for="name in ['public_key', 'private_key']"
            :key="name"
            class="configuration-field"
          >
            <label :for="`config-${name}`">{{ category.fields[name]?.label }}</label>
            <input
              :id="`config-${name}`"
              v-model="form[name]"
              :type="name === 'private_key' ? 'password' : 'text'"
              autocomplete="new-password"
              :disabled="!category.can_change || category.fields[name]?.locked || saving"
            />
          </div>
        </details>
      </template>
      <p v-if="!category.can_change">
        Du kannst diese Einstellungen ansehen. Änderungen erfordern das entsprechende
        Verwaltungsrecht.
      </p>
      <div class="configuration-actions">
        <Button
          label="Änderungen verwerfen"
          severity="secondary"
          outlined
          type="button"
          :disabled="!dirty || saving"
          @click="reset"
        />
        <Button
          label="Speichern"
          type="submit"
          :loading="saving"
          :disabled="!category.can_change || !dirty || saving"
        />
      </div>
      <details class="contract-details">
        <summary>Speicherort, Regeln und Herkunft</summary>
        <p v-for="[name, field] in Object.entries(category.fields)" :key="name">
          <strong>{{ field.label }}:</strong> {{ storageLabel(field.storage) }} ·
          {{ sourceLabel(field.source) }} · {{ effectiveLabel(field.effective)
          }}<template v-if="field.min != null"> · mindestens {{ field.min }}</template
          ><template v-if="field.max != null"> · höchstens {{ field.max }}</template>
        </p>
      </details>
    </form>
  </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import Button from 'primevue/button'
import Message from 'primevue/message'
import {
  configurationApi,
  configurationError,
  type ConfigurationCategory,
  type ConfigurationValue,
} from '@/api/configuration'
import { useClientConfiguration } from '@/composables/useClientConfiguration'
const props = defineProps<{ kind: string }>()
const category = ref<ConfigurationCategory | null>(null)
const values = ref<Record<string, ConfigurationValue>>({})
const form = ref<Record<string, ConfigurationValue>>({})
const units = ref<Record<string, string>>({})
const confirmKeyRemoval = ref(false)
function unitSeconds(name: string) {
  return { minutes: 60, hours: 3600, days: 86400 }[units.value[name] || 'hours'] || 3600
}

const loading = ref(false),
  saving = ref(false),
  error = ref(''),
  success = ref('')
const { refresh } = useClientConfiguration()
let generation = 0
function sourceLabel(source: string) {
  return (
    {
      default: 'Standardwert',
      computed: 'Abgeleiteter Wert',
      database: 'Organisationseinstellung',
      environment: 'Hostkonfiguration',
    }[source] || source
  )
}
function storageLabel(storage: string) {
  if (storage === 'derived') return 'Aus anderen Einstellungen abgeleitet'
  return storage.includes('encrypted') ? 'Verschlüsselt in der Datenbank' : 'Datenbank'
}
function effectiveLabel(effective: string) {
  return (
    { next_session_check: 'Nächste Sitzungsprüfung', next_push_operation: 'Nächster Push-Vorgang' }[
      effective
    ] || effective
  )
}
const visibleFields = computed(() =>
  Object.entries(category.value?.fields || {}).filter(
    ([name]) => !(props.kind === 'push' && ['public_key', 'private_key'].includes(name)),
  ),
)
function initialValue(name: string): ConfigurationValue {
  return category.value?.fields[name]?.secret ? '' : (values.value[name] ?? '')
}
function changes(): Record<string, ConfigurationValue> {
  const result: Record<string, ConfigurationValue> = {}
  for (const [name, field] of Object.entries(category.value?.fields || {})) {
    if (field.locked) continue
    const value = field.type === 'integer' ? Number(form.value[name]) : (form.value[name] ?? '')
    if (value !== initialValue(name) && !(field.secret && !value)) result[name] = value
  }
  return result
}
const dirty = computed(() => Object.keys(changes()).length > 0)
function reset() {
  confirmKeyRemoval.value = false
  for (const name of Object.keys(category.value?.fields || {})) {
    if (!units.value[name]) units.value[name] = name.startsWith('privileged_') ? 'hours' : 'days'
  }
  form.value = Object.fromEntries(
    Object.keys(category.value?.fields || {}).map((name) => [name, initialValue(name)]),
  )
  error.value = ''
  success.value = ''
}
async function load() {
  const token = ++generation
  loading.value = true
  category.value = null
  error.value = ''
  success.value = ''
  try {
    const [catalog, response] = await Promise.all([
      configurationApi.catalog(),
      configurationApi.get(props.kind),
    ])
    if (token !== generation) return
    const contract = catalog.data.categories[props.kind]
    if (!contract) throw new Error('permission')
    category.value = contract
    values.value = response.data
    reset()
  } catch (err) {
    if (token === generation) error.value = configurationError(err)
  } finally {
    if (token === generation) loading.value = false
  }
}
async function save() {
  if (!category.value?.can_change || !dirty.value || saving.value) return
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const response = await configurationApi.update(props.kind, changes())
    for (const name of Object.keys(changes())) {
      const field = category.value.fields[name]
      if (field && field.source !== 'environment') field.source = 'database'
    }
    values.value = response.data
    reset()
    success.value = 'Einstellungen gespeichert.'
    if (['training', 'vocabulary'].includes(props.kind))
      void refresh().catch(() => {
        /* New clients still read saved DB defaults. */
      })
  } catch (err) {
    error.value = configurationError(err)
  } finally {
    saving.value = false
  }
}
async function generateKeys() {
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const response = await configurationApi.generatePushKeys(String(form.value.subject || ''))
    values.value = response.data
    reset()
    success.value = 'Versandschlüssel erzeugt. Push kann jetzt aktiviert werden.'
  } catch (err) {
    error.value = configurationError(err)
  } finally {
    saving.value = false
  }
}
async function removeKeys() {
  if (
    !confirmKeyRemoval.value ||
    !category.value?.can_change ||
    category.value.fields.private_key?.locked
  )
    return
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const response = await configurationApi.update('push', {
      enabled: false,
      public_key: '',
      private_key: '',
      subject: '',
    })
    values.value = response.data
    reset()
    success.value =
      'Push ausgeschaltet und Schlüssel entfernt. Ein neues Schlüsselpaar kann jetzt erzeugt werden.'
  } catch (err) {
    error.value = configurationError(err)
  } finally {
    saving.value = false
  }
}
function allowLeave() {
  return saving.value
    ? false
    : !dirty.value || window.confirm('Ungespeicherte Einstellungen verwerfen?')
}
onBeforeRouteLeave(allowLeave)
onBeforeRouteUpdate(allowLeave)
function beforeUnload(event: BeforeUnloadEvent) {
  if (dirty.value || saving.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}
window.addEventListener('beforeunload', beforeUnload)
onBeforeUnmount(() => {
  generation++
  window.removeEventListener('beforeunload', beforeUnload)
})
watch(() => props.kind, load, { immediate: true })
</script>
<style scoped>
.configuration-section {
  max-width: 820px;
  padding: 1.5rem;
}
h2 {
  margin-bottom: 0.5rem;
}
p,
small {
  line-height: 1.6;
}
.configuration-field {
  display: grid;
  gap: 0.4rem;
  margin: 1.25rem 0;
}
.configuration-field label {
  font-weight: 600;
}
.configuration-field input:not([type='checkbox']),
.configuration-field textarea {
  width: 100%;
  font: inherit;
  resize: vertical;
  min-height: 44px;
  padding: 0.65rem;
  background: var(--p-form-field-background);
  color: var(--p-form-field-color);
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 6px;
}
.configuration-field input[type='checkbox'] {
  width: 24px;
  height: 24px;
}
small {
  color: var(--jf-color-text-muted);
}
.duration-input {
  display: flex;
  gap: 0.75rem;
}
.duration-input select {
  min-width: 90px;
  min-height: 44px;
  background: var(--p-form-field-background);
  color: var(--jf-color-text);
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 6px;
}
.configuration-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 1.5rem 0;
}
.contract-details {
  margin-top: 2rem;
}
summary {
  cursor: pointer;
  min-height: 44px;
}
input:focus-visible,
summary:focus-visible {
  outline: var(--jf-focus-ring);
}
</style>
