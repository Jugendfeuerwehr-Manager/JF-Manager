<template>
  <section class="health-card" aria-labelledby="health-heading">
    <header class="health-card__header">
      <div class="health-card__title">
        <i class="pi pi-heart" aria-hidden="true"></i>
        <h2 id="health-heading">Gesundheitsangaben</h2>
      </div>
      <span class="health-card__privacy">
        <i class="pi pi-lock" aria-hidden="true"></i>Verschlüsselt · jedes Einblenden wird protokolliert
      </span>
    </header>

    <Message v-if="membersStore.healthError" severity="error" :closable="false">{{ membersStore.healthError }}</Message>

    <template v-if="revealed">
      <div v-if="editing" class="health-card__field">
        <label for="health-notes-input" class="health-card__label">Allergien, Medikamente, Notfallhinweise</label>
        <Textarea
          id="health-notes-input"
          v-model="draft"
          rows="4"
          auto-resize
          maxlength="4000"
          placeholder="z. B. Allergie gegen Wespenstiche, Notfallset im Rucksack"
          aria-describedby="health-notes-hint"
        />
        <p id="health-notes-hint" class="health-card__hint">Nur Angaben, die bei Übungen und Ausfahrten wichtig sind.</p>
      </div>
      <template v-else>
        <span class="health-card__label">Hinterlegte Angaben</span>
        <p v-if="text" id="health-notes" class="health-card__value">{{ text }}</p>
        <p v-else class="health-card__empty">Keine Gesundheitsangaben hinterlegt.</p>
      </template>
      <div class="health-card__actions">
        <template v-if="editing">
          <Button label="Speichern" icon="pi pi-check" :loading="membersStore.healthLoading" @click="save" />
          <Button label="Abbrechen" severity="secondary" text @click="cancelEdit" />
        </template>
        <template v-else>
          <Button v-if="canEdit" label="Bearbeiten" icon="pi pi-pencil" severity="secondary" outlined @click="startEdit" />
          <Button label="Ausblenden" icon="pi pi-eye-slash" severity="secondary" text @click="hide" />
        </template>
      </div>
    </template>
    <div v-else class="health-card__concealed">
      <span class="health-card__empty">{{ stored ? 'Angaben sind hinterlegt und ausgeblendet.' : 'Keine Angaben hinterlegt.' }}</span>
      <Button
        :label="stored || !canEdit ? 'Einblenden' : 'Erfassen'"
        :icon="stored || !canEdit ? 'pi pi-eye' : 'pi pi-plus'"
        severity="secondary"
        outlined
        :loading="membersStore.healthLoading"
        @click="reveal"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { useMembersStore } from '@/stores/members'

interface Props {
  memberId: number
  hasNotes: boolean
  canEdit: boolean
}

const props = defineProps<Props>()
const membersStore = useMembersStore()
const revealed = ref(false)
const editing = ref(false)
const draft = ref('')
const text = computed(() => membersStore.healthNotes[props.memberId] ?? '')
// Whether anything is stored. Starts from the member record and follows what was
// last loaded or saved here, so hiding after an edit does not claim "keine Angaben".
const stored = ref(props.hasNotes)
watch(() => props.hasNotes, (value) => { stored.value = value })

async function reveal() {
  // The server asks for a fresh confirmation; the API client shows the prompt and retries.
  if (await membersStore.fetchHealthNotes(props.memberId)) {
    stored.value = !!text.value
    revealed.value = true
    if (!text.value && props.canEdit) startEdit()
  }
}

function startEdit() {
  draft.value = text.value
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  // Nothing was stored yet: go back to the concealed state instead of an empty box.
  if (!text.value) hide()
}

async function save() {
  if (await membersStore.saveHealthNotes(props.memberId, draft.value)) {
    stored.value = !!text.value
    editing.value = false
  }
}

function hide() {
  revealed.value = false
  editing.value = false
  membersStore.forgetHealthNotes(props.memberId)
}

// Never keep health data in memory longer than the view is open.
onBeforeUnmount(() => membersStore.forgetHealthNotes(props.memberId))
</script>

<style scoped>
.health-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-2) var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
}

.health-card__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.health-card__title {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  color: var(--jf-color-primary);
}

.health-card__title h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}

.health-card__privacy,
.health-card__hint,
.health-card__empty {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.health-card__privacy {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.health-card__privacy i {
  font-size: 0.75rem;
}

.health-card__label {
  font-size: 0.75rem;
  font-weight: var(--jf-weight-semibold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}

.health-card__field {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
}

.health-card__field :deep(textarea) {
  width: 100%;
}

/* What the user entered: regular text on a framed surface, set apart from the explanations around it. */
.health-card__value {
  margin: 0;
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border-left: 3px solid var(--jf-color-primary);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  color: var(--jf-color-text);
  font-size: 0.9375rem;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.health-card__concealed {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px dashed var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.health-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
}
</style>
