<template>
  <div class="handout-page">
    <div class="handout-toolbar">
      <Button icon="pi pi-arrow-left" text @click="$router.back()" label="Zurück" />
      <div class="spacer" />
      <Button icon="pi pi-print" label="Drucken" outlined size="small" @click="printPage" />
      <Button icon="pi pi-file-pdf" label="PDF herunterladen" size="small" :loading="generatingPdf" @click="downloadPdf" />
    </div>

    <p v-if="pdfError" role="alert">{{ pdfError }}</p>
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
    </div>

    <div v-else-if="handout" id="handout-print-area">
      <TrainingHandout :handout="handout" :org-name="branding?.title ?? ''" :logo-url="branding?.logo_url ?? ''" />
    </div>

    <div v-else class="error-state">
      <p>Handout konnte nicht geladen werden.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { mediaBlob } from '@/utils/privateMedia'
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import TrainingHandout from '@/components/training/organisms/TrainingHandout.vue'
import { brandingApi } from '@/api/branding'
import { buildHandoutPdf, type HandoutTheme } from '@/components/training/utils/handoutPdf'
import { htmlToPdfContent } from '@/components/training/utils/handoutPdfHtml'
import { useTrainingStore } from '@/stores/training'
import { currentBrandColor } from '@/theme/applyBrand'
import { BRAND_MARK_SVG } from '@/theme/brandMark'
import type { PublicBranding } from '@/types/settings'

const route = useRoute()
const trainingStore = useTrainingStore()
const generatingPdf = ref(false)
const pdfError = ref('')
const sessionId = computed(() => Number(route.params.id))
const handout = computed(() => trainingStore.handout)
const loading = computed(() => trainingStore.loading)

const branding = ref<PublicBranding | null>(null)

onMounted(() => {
  void trainingStore.fetchHandout(sessionId.value)
  void brandingApi.getPublicBranding().then((r) => { branding.value = r.data }).catch(() => undefined)
})

function printPage() {
  window.print()
}

/**
 * Loads an image as a data URL pdfmake can embed. pdfmake only reads PNG and
 * JPEG, so other formats (SVG logos, WebP photos) are redrawn as PNG.
 */
async function loadImage(src: string): Promise<string | null> {
  try {
    const blob = await mediaBlob(src)
    if (blob.type === 'image/png' || blob.type === 'image/jpeg') {
      return await new Promise((resolve) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result as string)
        reader.onerror = () => resolve(null)
        reader.readAsDataURL(blob)
      })
    }
    const url = URL.createObjectURL(blob)
    try {
      const img = new Image()
      img.src = url
      await img.decode()
      // Upscale small vector logos so they stay sharp in print.
      const scale = Math.max(1, 400 / (img.naturalWidth || 400))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round((img.naturalWidth || 400) * scale)
      canvas.height = Math.round((img.naturalHeight || 400) * scale)
      canvas.getContext('2d')?.drawImage(img, 0, 0, canvas.width, canvas.height)
      return canvas.toDataURL('image/png')
    } finally {
      URL.revokeObjectURL(url)
    }
  } catch {
    return null
  }
}

/**
 * Organisation branding as the app shows it: the colour currently applied,
 * the organisation logo, or the product mark when there is none.
 */
async function loadTheme(): Promise<Partial<HandoutTheme>> {
  const logoUrl = branding.value?.logo_url
  const logo = logoUrl ? await loadImage(logoUrl) : null
  return {
    brandColor: currentBrandColor(),
    orgName: branding.value?.title ?? '',
    logo: logo ? { image: logo } : { svg: BRAND_MARK_SVG },
  }
}

async function downloadPdf() {
  if (!handout.value) return
  generatingPdf.value = true
  pdfError.value = ''
  try {
    const [{ default: pdfMake }, { default: pdfFonts }, theme] = await Promise.all([
      import('pdfmake/build/pdfmake'),
      import('pdfmake/build/vfs_fonts'),
      loadTheme(),
    ])
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const pdfMakeTyped = pdfMake as any
    pdfMakeTyped.addVirtualFileSystem(pdfFonts)

    const docDef = await buildHandoutPdf(handout.value, {
      theme,
      renderHtml: (html) => htmlToPdfContent(html, loadImage),
    })
    await pdfMakeTyped.createPdf(docDef).download(`handout-${sessionId.value}.pdf`)
  } catch {
    pdfError.value = 'PDF konnte nicht erstellt werden. Bitte erneut versuchen.'
  } finally {
    generatingPdf.value = false
  }
}
</script>

<style scoped>
.handout-page { display: flex; flex-direction: column; min-height: 100vh; }
/* Auto margins disable stretching in the flex column; without a width the
   area grew to its content and widened the page on phones. */
#handout-print-area { width: 100%; min-width: 0; box-sizing: border-box; }

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
