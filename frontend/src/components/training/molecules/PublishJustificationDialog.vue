<template>
  <Dialog :visible="visible" header="Trotz Warnungen veröffentlichen?" modal :style="{ width: '600px', maxWidth: 'calc(100vw - 24px)' }" @update:visible="emit('update:visible', $event)">
    <form class="justify" @submit.prevent="confirm">
      <p>Die Übung hat folgende Planungswarnungen. Die Begründung wird mit der Veröffentlichung gespeichert.</p>
      <ul>
        <li v-for="(warning, index) in warnings" :key="index">{{ warning }}</li>
      </ul>
      <label for="publish-justification">Begründung *</label>
      <Textarea id="publish-justification" v-model="text" rows="3" auto-resize required />
      <div class="justify__actions">
        <Button type="button" label="Abbrechen" severity="secondary" @click="emit('update:visible', false)" />
        <Button type="submit" label="Mit Begründung veröffentlichen" :disabled="!text.trim()" />
      </div>
    </form>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'

const props = defineProps<{ visible: boolean; warnings: string[]; initial?: string }>()
const emit = defineEmits<{ 'update:visible': [visible: boolean]; confirm: [justification: string] }>()
const text = ref('')

watch(() => props.visible, (visible) => { if (visible) text.value = props.initial ?? '' }, { immediate: true })

function confirm() {
  if (!text.value.trim()) return
  emit('confirm', text.value.trim())
  emit('update:visible', false)
}
</script>

<style scoped>
.justify { display: grid; gap: var(--jf-space-2); }
.justify p, .justify ul { margin: 0; }
.justify label { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); color: var(--jf-color-text-muted); }
.justify__actions { display: flex; justify-content: flex-end; gap: var(--jf-space-2); }
</style>
