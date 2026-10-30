<template>
  <div class="legal-editor">
    <div class="legal-editor__status">
      <Tag v-if="page.current_version" severity="success" :value="`Veröffentlicht: Version ${page.current_version.version}`" />
      <Tag v-else severity="warn" value="Noch nicht veröffentlicht" />
      <Tag v-if="page.has_unpublished_changes && page.current_version" severity="info" value="Ungespeicherte Änderungen gegenüber der Veröffentlichung" />
      <a v-if="page.current_version" :href="publicPath" target="_blank" rel="noopener" class="legal-editor__link">
        Öffentliche Seite ansehen <i class="pi pi-external-link" />
      </a>
    </div>

    <div class="field">
      <label :for="`legal-title-${page.kind}`">Titel</label>
      <InputText :id="`legal-title-${page.kind}`" v-model="title" :disabled="!canEdit" class="w-full" maxlength="200" />
    </div>
    <div class="field">
      <label>Text</label>
      <TiptapEditor v-if="canEdit" v-model="body" :show-variables="false" placeholder="Text eingeben …" />
      <div v-else class="legal-editor__readonly" v-html="safeBody" />
    </div>

    <div v-if="canEdit" class="legal-editor__actions">
      <Button label="Entwurf speichern" icon="pi pi-save" severity="secondary" :loading="saving" :disabled="!dirty" @click="saveDraft" />
      <InputText v-model="changeNote" placeholder="Änderungshinweis (optional)" maxlength="300" class="legal-editor__note" />
      <Button label="Veröffentlichen" icon="pi pi-send" :loading="saving" @click="publish" />
    </div>
    <p v-if="canEdit" class="legal-editor__hint">
      Veröffentlichen friert den Entwurf als neue Version ein. Einwilligungen verweisen auf diese Version; ältere Versionen bleiben erhalten.
    </p>

    <h4 class="legal-editor__versions-title">Versionen</h4>
    <p v-if="!versions.length" class="legal-editor__hint">Noch keine Version veröffentlicht.</p>
    <ul v-else class="legal-editor__versions">
      <li v-for="version in versions" :key="version.version">
        <strong>Version {{ version.version }}</strong> · {{ formatDate(version.published_at) }}
        <span v-if="version.published_by_name"> · {{ version.published_by_name }}</span>
        <span v-if="version.change_note" class="legal-editor__note-text"> – {{ version.change_note }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import TiptapEditor from '@/components/emails/organisms/TiptapEditor.vue'
import type { LegalPage, LegalPageVersion } from '@/types/privacy'
import { sanitizeRichHtml } from '@/utils/htmlSafety'

interface Props {
  page: LegalPage
  versions: LegalPageVersion[]
  canEdit: boolean
  saving: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  save: [data: { draft_title: string, draft_body: string }]
  publish: [data: { draft_title: string, draft_body: string, change_note: string }]
}>()

const title = ref(props.page.draft_title)
const body = ref(props.page.draft_body)
const changeNote = ref('')

watch(() => props.page, page => {
  title.value = page.draft_title
  body.value = page.draft_body
})

const dirty = computed(() => title.value !== props.page.draft_title || body.value !== props.page.draft_body)
const safeBody = computed(() => sanitizeRichHtml(props.page.draft_body))
const publicPath = computed(() => (props.page.kind === 'imprint' ? '/impressum' : '/datenschutz'))

function formatDate(value: string) {
  return new Date(value).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' })
}

function saveDraft() {
  emit('save', { draft_title: title.value, draft_body: body.value })
}

function publish() {
  emit('publish', { draft_title: title.value, draft_body: body.value, change_note: changeNote.value })
  changeNote.value = ''
}
</script>

<style scoped>
.legal-editor { display: flex; flex-direction: column; gap: 1rem; }
.legal-editor__status { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.legal-editor__link { font-size: .875rem; }
.legal-editor .field { display: flex; flex-direction: column; gap: .375rem; margin: 0; }
.legal-editor__readonly { border: 1px solid var(--p-content-border-color); border-radius: 6px; padding: .75rem 1rem; }
.legal-editor__actions { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.legal-editor__note { flex: 1 1 14rem; }
.legal-editor__hint { color: var(--text-color-secondary); font-size: .85rem; margin: 0; }
.legal-editor__versions-title { margin: .5rem 0 0; }
.legal-editor__versions { margin: 0; padding-left: 1.25rem; display: flex; flex-direction: column; gap: .25rem; font-size: .9rem; }
.legal-editor__note-text { color: var(--text-color-secondary); }
</style>
