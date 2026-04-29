<template>
  <div class="handout-page">
    <div class="handout-toolbar">
      <Button icon="pi pi-arrow-left" text @click="$router.back()" label="Zurück" />
      <div class="spacer" />
      <Button icon="pi pi-print" label="Drucken" outlined size="small" @click="printPage" />
      <Button icon="pi pi-file-pdf" label="PDF herunterladen" size="small" :loading="generatingPdf" @click="downloadPdf" />
    </div>

    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
    </div>

    <div v-else-if="handout" id="handout-print-area">
      <TrainingHandout :handout="handout" />
    </div>

    <div v-else class="error-state">
      <p>Handout konnte nicht geladen werden.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import TrainingHandout from '@/components/training/organisms/TrainingHandout.vue'
import { useTrainingStore } from '@/stores/training'
import type { Content } from 'pdfmake/interfaces'

const route = useRoute()
const trainingStore = useTrainingStore()
const generatingPdf = ref(false)
const sessionId = computed(() => Number(route.params.id))
const handout = computed(() => trainingStore.handout)
const loading = computed(() => trainingStore.loading)

onMounted(() => trainingStore.fetchHandout(sessionId.value))

function printPage() {
  window.print()
}

async function downloadPdf() {
  generatingPdf.value = true
  try {
    const { default: pdfMake } = await import('pdfmake/build/pdfmake')
    const { default: pdfFonts } = await import('pdfmake/build/vfs_fonts')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pdfMakeTyped = pdfMake as any
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    pdfMakeTyped.vfs = (pdfFonts as any).pdfMake?.vfs ?? (pdfFonts as any).vfs

    if (!handout.value) return

    const h = handout.value
    const dateStr = new Date(h.date).toLocaleDateString('de-DE', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    })

    const content: Content[] = [
      { text: h.title, style: 'h1' },
      { text: `${dateStr}${h.start_time ? ' · ' + h.start_time : ''}${h.location ? ' · ' + h.location : ''}`, style: 'meta' },
      { text: '\n' },
      { text: 'Übungsablauf', style: 'h2' },
      {
        table: {
          headerRows: 1,
          widths: [60, '*', 60, 80],
          body: [
            ['Zeit', 'Ausbildungspunkt', 'Dauer', 'Gruppe'].map((h) => ({ text: h, bold: true, fillColor: '#f1f5f9' })),
            ...h.blocks.map((b) => [
              offsetToTime(b.start_offset_minutes, h.start_time),
              b.title,
              `${b.duration_minutes} Min.`,
              b.groups?.length ? b.groups.map((g) => g.name).join(', ') : 'Alle',
            ]),
          ],
        },
        margin: [0, 0, 0, 16],
      },
    ]

    for (const block of h.blocks) {
      content.push({ text: block.title, style: 'h3' } as Content)
      if (block.content) {
        // Strip HTML tags for PDF (simple fallback)
        const plain = block.content.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
        content.push({ text: plain, style: 'body' })
      }
    }

    const docDef = {
      content,
      styles: {
        h1: { fontSize: 20, bold: true, margin: [0, 0, 0, 4] },
        h2: { fontSize: 14, bold: true, margin: [0, 12, 0, 6] },
        h3: { fontSize: 12, bold: true, margin: [0, 10, 0, 4] },
        meta: { fontSize: 10, color: '#666', margin: [0, 0, 0, 12] },
        body: { fontSize: 10, lineHeight: 1.4, margin: [0, 0, 0, 8] },
      },
      pageMargins: [40, 40, 40, 40] as [number, number, number, number],
    }

    pdfMakeTyped.createPdf(docDef).download(`handout-${sessionId.value}.pdf`)
  } finally {
    generatingPdf.value = false
  }
}

function offsetToTime(offsetMinutes: number | null | undefined, startTime?: string | null): string {
  if (!startTime || offsetMinutes == null) return '—'
  const parts = startTime.split(':')
  const h = Number(parts[0] ?? 0)
  const m = Number(parts[1] ?? 0)
  const total = h * 60 + m + offsetMinutes
  return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}
</script>

<style scoped>
.handout-page { display: flex; flex-direction: column; min-height: 100vh; }

.handout-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
  flex-shrink: 0;
}
.spacer { flex: 1; }

#handout-print-area { padding: 1.5rem; max-width: 960px; margin: 0 auto; }

.loading-state, .error-state {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

@media print {
  .handout-toolbar { display: none; }
  #handout-print-area { padding: 0; max-width: 100%; }
  .handout-page { min-height: auto; }
}
</style>
