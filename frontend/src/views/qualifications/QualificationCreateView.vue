<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import QualificationForm from '@/components/qualifications/organisms/QualificationForm.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import StateView from '@/components/common/StateView.vue'
import { useToast } from 'primevue/usetoast'
import type { Qualification } from '@/types/qualifications'
import { formatDate } from '@/components/qualifications/utils/qualificationStatus'

const route = useRoute()
const router = useRouter()
const qualificationsStore = useQualificationsStore()
const toast = useToast()

// `?renew=<id>` starts a renewal of an existing qualification.
const renewId = computed(() => Number(route.query.renew) || null)
const renewFrom = ref<Qualification | null>(null)
const loadingSource = ref(false)
const sourceError = ref(false)

async function loadSource() {
  if (!renewId.value) return
  loadingSource.value = true
  sourceError.value = false
  try {
    renewFrom.value = (await qualificationsStore.fetchQualification(renewId.value)) ?? null
    sourceError.value = !renewFrom.value
  } catch {
    sourceError.value = true
  } finally {
    loadingSource.value = false
  }
}

onMounted(async () => {
  await Promise.all([qualificationsStore.fetchQualificationTypes(), loadSource()])
})

function handleFormSuccess(qualificationId: number) {
  toast.add({
    severity: 'success',
    summary: renewFrom.value ? 'Verlängert' : 'Gespeichert',
    detail: renewFrom.value ? 'Die bisherige Qualifikation bleibt als Verlauf erhalten.' : 'Qualifikation wurde angelegt.',
    life: 3000
  })
  router.push({ name: 'qualification-detail', params: { id: String(qualificationId) } })
}

function handleFormCancel() {
  router.push(renewId.value ? `/qualifications/${renewId.value}` : '/qualifications')
}
</script>

<template>
  <div class="qualification-create">
    <OverviewHeader
      eyebrow="Qualifikationen"
      :title="renewId ? 'Qualifikation verlängern' : 'Neue Qualifikation'"
      :subtitle="renewFrom ? `${renewFrom.type_name} · ${renewFrom.person_name} · bisher gültig bis ${formatDate(renewFrom.date_expires)}` : undefined"
    />
    <StateView v-if="loadingSource" kind="loading" />
    <StateView
      v-else-if="sourceError"
      kind="error"
      title="Zu verlängernde Qualifikation nicht gefunden"
      message="Sie wurde gelöscht oder du hast keinen Zugriff darauf."
      @retry="loadSource"
    />
    <QualificationForm
      v-else
      :key="renewFrom?.id ?? 'new'"
      :renew-from="renewFrom ?? undefined"
      @success="handleFormSuccess"
      @cancel="handleFormCancel"
    />
  </div>
</template>

<style scoped>
.qualification-create { display: flex; flex-direction: column; gap: var(--jf-space-2); }
</style>
