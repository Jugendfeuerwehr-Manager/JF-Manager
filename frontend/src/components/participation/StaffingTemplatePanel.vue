<template>
  <section class="tpl" aria-labelledby="tpl-title">
    <h3 id="tpl-title" class="tpl__title">Besetzungsvorlage</h3>
    <p v-if="source" class="tpl__hint"><i class="pi pi-copy" aria-hidden="true"></i>Übernommen aus „{{ source.name }}“. Spätere Änderungen der Vorlage wirken nicht auf diesen Dienst.</p>
    <p v-else class="tpl__hint">Modus, Voraussetzungen, Positionen, Zahlen und Warteliste aus einer Vorlage übernehmen oder als Vorlage speichern.</p>

    <p v-if="templates.error" class="tpl__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ templates.error }}</p>
    <p v-if="message" class="tpl__notice" role="status"><i :class="messageIcon" aria-hidden="true"></i>{{ message }}</p>
    <ul v-if="warnings.length" class="tpl__warnings" role="status">
      <li v-for="w in warnings" :key="w"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> {{ w }}</li>
    </ul>

    <div v-if="!readonly" class="tpl__row">
      <div class="tpl__field">
        <label for="tpl-select">Vorlage</label>
        <select id="tpl-select" v-model="selected" class="tpl__input" :disabled="templates.loading || !active.length">
          <option :value="null">{{ templates.loading ? 'Wird geladen …' : active.length ? 'Vorlage wählen' : 'Keine Vorlagen vorhanden' }}</option>
          <option v-for="t in active" :key="t.id" :value="t.id">{{ t.name }}{{ t.scope === 'organization' ? ' (Organisation)' : '' }}</option>
        </select>
      </div>
      <Button label="Anwenden" icon="pi pi-download" severity="secondary" :disabled="selected === null || store.saving" @click="askApply" />
      <Button label="Als Vorlage speichern" icon="pi pi-save" severity="secondary" outlined :disabled="store.dirty" :title="store.dirty ? 'Erst speichern, dann als Vorlage sichern' : undefined" @click="openSave" />
    </div>
    <p v-if="chosen" class="tpl__hint">
      {{ modeLabel(chosen.mode) }}<template v-if="chosen.slots.length"> · {{ chosen.slots.map(s => `${s.label} (${s.min}/${s.max})`).join(', ') }}</template><template v-if="chosen.summary"> · {{ chosen.summary }}</template>
    </p>

    <details v-if="!readonly" class="tpl__manage" @toggle="onManage">
      <summary>Vorlagen verwalten</summary>
      <label class="tpl__check"><input :checked="templates.showArchived" type="checkbox" @change="templates.load(department, ($event.target as HTMLInputElement).checked)">Archivierte anzeigen</label>
      <ul class="tpl__list">
        <li v-for="t in templates.templates" :key="t.id">
          <span>
            <strong>{{ t.name }}</strong>
            <span class="tpl__hint">{{ t.scope === 'organization' ? 'Organisation' : t.department_name }}<template v-if="t.archived"> · archiviert</template></span>
          </span>
          <Button
            v-if="t.scope === 'department' || templates.canManageOrganization"
            :label="t.archived ? 'Wiederherstellen' : 'Archivieren'"
            :icon="t.archived ? 'pi pi-replay' : 'pi pi-inbox'"
            size="small" text severity="secondary"
            :aria-label="`${t.name} ${t.archived ? 'wiederherstellen' : 'archivieren'}`"
            :disabled="templates.busy"
            @click="templates.setArchived(t, !t.archived)"
          />
        </li>
      </ul>
    </details>

    <Dialog v-model:visible="confirmOpen" modal header="Vorlage anwenden" :style="{ width: '28rem', maxWidth: 'calc(100vw - 24px)' }">
      <p>Die Teilnahme-Einstellungen dieses Dienstes werden durch „{{ chosen?.name }}“ ersetzt (Modus, Voraussetzungen, Positionen, Zahlen, Warteliste). Fristen und Hinweis bleiben.</p>
      <p v-if="store.dirty" class="tpl__warn"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> Ungespeicherte Änderungen gehen verloren.</p>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" text @click="confirmOpen = false" />
        <Button label="Anwenden" icon="pi pi-check" :loading="store.saving" @click="apply" />
      </template>
    </Dialog>

    <Dialog v-model:visible="saveOpen" modal header="Als Besetzungsvorlage speichern" :style="{ width: '30rem', maxWidth: 'calc(100vw - 24px)' }">
      <div class="tpl__form">
        <label for="tpl-name">Name</label>
        <input id="tpl-name" v-model="name" class="tpl__input" maxlength="120" placeholder="z. B. Brandsicherheitswache">
        <label for="tpl-description">Beschreibung (optional)</label>
        <textarea id="tpl-description" v-model="description" class="tpl__input tpl__textarea" rows="2" maxlength="1000"></textarea>
        <fieldset class="tpl__scope">
          <legend>Gilt für</legend>
          <label class="tpl__check"><input v-model="scope" type="radio" value="department">Diese Abteilung</label>
          <label class="tpl__check" :class="{ 'tpl__check--off': !templates.canManageOrganization }">
            <input v-model="scope" type="radio" value="organization" :disabled="!templates.canManageOrganization">Ganze Organisation
            <span v-if="!templates.canManageOrganization" class="tpl__hint">(nur organisationsweite Planung)</span>
          </label>
        </fieldset>
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" text @click="saveOpen = false" />
        <Button label="Speichern" icon="pi pi-save" :disabled="!name.trim()" :loading="templates.busy" @click="save" />
      </template>
    </Dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { useParticipationStore } from '@/stores/participation'
import { useStaffingTemplatesStore } from '@/stores/staffingTemplates'
import type { ParticipationMode } from '@/api/participation'

const props = defineProps<{ sessionId: number, department: number | null, readonly?: boolean }>()
const store = useParticipationStore()
const templates = useStaffingTemplatesStore()

const selected = ref<number | null>(null)
const confirmOpen = ref(false)
const saveOpen = ref(false)
const name = ref('')
const description = ref('')
const scope = ref<'department' | 'organization'>('department')
const message = ref<string | null>(null)
const messageIcon = ref('pi pi-check')
const warnings = ref<string[]>([])

const source = computed(() => store.config?.template_source ?? null)
const active = computed(() => templates.templates.filter(t => !t.archived))
const chosen = computed(() => active.value.find(t => t.id === selected.value) ?? null)
const modeLabel = (mode: ParticipationMode | null) => ({ opt_out: 'Abmeldung', opt_in: 'Anmeldung', assignment: 'Zuteilung' }[mode ?? 'opt_in'])

function askApply() { if (selected.value !== null) confirmOpen.value = true }

async function apply() {
  if (selected.value === null) return
  const result = await store.applyTemplate(selected.value)
  confirmOpen.value = false
  warnings.value = result.warnings ?? []
  message.value = result.ok ? `Vorlage übernommen.${warnings.value.length ? ' Bitte die Hinweise prüfen.' : ''}` : result.message ?? null
  messageIcon.value = result.ok ? 'pi pi-check' : 'pi pi-exclamation-circle'
}

function openSave() {
  name.value = ''
  description.value = ''
  scope.value = 'department'
  saveOpen.value = true
}

async function save() {
  const created = await templates.create({
    name: name.value.trim(),
    description: description.value.trim(),
    department: scope.value === 'organization' ? null : props.department,
    session: props.sessionId,
  })
  if (created) {
    saveOpen.value = false
    message.value = `Als Vorlage „${created.name}“ gespeichert.`
    messageIcon.value = 'pi pi-check'
  }
}

function onManage(event: Event) {
  if ((event.target as HTMLDetailsElement).open && !templates.templates.length) void templates.load(props.department)
}

onMounted(() => { if (!props.readonly) void templates.load(props.department, false) })
watch(() => props.department, dept => { if (!props.readonly) void templates.load(dept, false) })
</script>

<style scoped>
.tpl { display: grid; gap: var(--jf-space-1-5); padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); min-width: 0; }
.tpl p { margin: 0; }
.tpl__title { margin: 0; font-size: var(--jf-text-lg); font-weight: var(--jf-weight-bold); }
.tpl__hint { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.tpl__hint i, .tpl__notice i, .tpl__error i { margin-right: var(--jf-space-0-5); }
.tpl__row { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); align-items: flex-end; }
.tpl__row :deep(.p-button) { min-height: var(--jf-touch-target); }
.tpl__field { display: grid; gap: var(--jf-space-0-5); flex: 1 1 14rem; }
.tpl__field label, .tpl__form > label { font-weight: var(--jf-weight-semibold); }
.tpl__input { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; box-sizing: border-box; width: 100%; }
.tpl__textarea { padding: var(--jf-space-1) var(--jf-space-1-5); resize: vertical; }
.tpl__form { display: grid; gap: var(--jf-space-1); }
.tpl__scope { border: 0; margin: 0; padding: 0; display: grid; gap: 2px; }
.tpl__scope legend { font-weight: var(--jf-weight-semibold); padding: 0; }
.tpl__check { display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); flex-wrap: wrap; }
.tpl__check--off { color: var(--jf-color-text-muted); }
.tpl__manage summary { min-height: var(--jf-touch-target); display: flex; align-items: center; cursor: pointer; font-weight: var(--jf-weight-semibold); }
.tpl__list { margin: 0; padding: 0; list-style: none; display: grid; gap: var(--jf-space-0-5); }
.tpl__list li { display: flex; justify-content: space-between; align-items: center; gap: var(--jf-space-1); }
.tpl__list li > span { display: grid; }
.tpl__warnings { margin: 0; padding: 0; list-style: none; font-size: var(--jf-text-sm); color: var(--p-amber-700); }
.tpl__warn { color: var(--p-amber-700); }
.tpl__error { color: var(--p-red-600); }
.app-dark .tpl__warnings, .app-dark .tpl__warn { color: var(--p-amber-300); }
.app-dark .tpl__error { color: var(--p-red-300); }
</style>
