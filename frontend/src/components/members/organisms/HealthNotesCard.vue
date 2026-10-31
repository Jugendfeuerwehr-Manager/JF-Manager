<template>
  <section class="detail-card aside-card health-card" aria-labelledby="health-heading">
    <div class="aside-card__title">
      <i class="pi pi-heart" aria-hidden="true"></i>
      <h2 id="health-heading">Gesundheitsangaben</h2>
    </div>
    <p class="muted">
      Allergien, Medikamente, Notfallhinweise. Verschlüsselt gespeichert; jedes Einblenden erfordert eine erneute Bestätigung und wird protokolliert.
    </p>
    <Message v-if="membersStore.healthError" severity="error" :closable="false">{{ membersStore.healthError }}</Message>

    <template v-if="revealed">
      <Textarea v-if="editing" v-model="draft" rows="4" auto-resize maxlength="4000" aria-label="Gesundheitsangaben" class="w-full" />
      <p v-else-if="text" id="health-notes" class="notes">{{ text }}</p>
      <p v-else class="muted">Keine Gesundheitsangaben hinterlegt.</p>
      <div class="health-card__actions">
        <template v-if="editing">
          <Button label="Speichern" :loading="membersStore.healthLoading" @click="save" />
          <Button label="Abbrechen" severity="secondary" text @click="editing = false" />
        </template>
        <template v-else>
          <Button v-if="canEdit" label="Bearbeiten" icon="pi pi-pencil" severity="secondary" outlined @click="startEdit" />
          <Button label="Ausblenden" severity="secondary" text @click="hide" />
        </template>
      </div>
    </template>
    <template v-else>
      <p class="muted">{{ hasNotes ? 'Angaben sind hinterlegt.' : 'Keine Angaben hinterlegt.' }}</p>
      <Button
        :label="hasNotes ? 'Einblenden' : canEdit ? 'Erfassen' : 'Einblenden'"
        :icon="hasNotes ? 'pi pi-eye' : 'pi pi-plus'"
        severity="secondary"
        outlined
        class="aside-card__button"
        :loading="membersStore.healthLoading"
        @click="reveal"
      />
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
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

async function reveal() {
  // The server asks for a fresh confirmation; the API client shows the prompt and retries.
  if (await membersStore.fetchHealthNotes(props.memberId)) {
    revealed.value = true
    if (!text.value && props.canEdit) startEdit()
  }
}

function startEdit() {
  draft.value = text.value
  editing.value = true
}

async function save() {
  if (await membersStore.saveHealthNotes(props.memberId, draft.value)) editing.value = false
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
.health-card__actions { display: flex; gap: .5rem; flex-wrap: wrap; }
</style>
