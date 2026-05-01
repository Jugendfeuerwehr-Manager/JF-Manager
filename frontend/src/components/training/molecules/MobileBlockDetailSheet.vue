<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="block" class="sheet-backdrop" @click.self="emit('close')">
        <div class="sheet" role="dialog" :aria-label="block.title">

          <!-- ── Drag handle bar ─────────────────────────────────── -->
          <div class="sheet-handle-row" @click="emit('close')">
            <div class="sheet-handle" />
          </div>

          <!-- ── Scrollable content ─────────────────────────────── -->
          <div class="sheet-scroll">

            <!-- Header -->
            <div class="sheet-header">
              <div class="sheet-header-left">
                <div class="sheet-time-badge">
                  {{ startTime }} – {{ endTime }}
                </div>
                <h2 class="sheet-title">{{ block.title }}</h2>
              </div>
              <button class="sheet-close" @click="emit('close')" aria-label="Schließen">
                <i class="pi pi-times" />
              </button>
            </div>

            <!-- Duration + meta chips -->
            <div class="sheet-chips">
              <span class="chip chip--duration">
                <i class="pi pi-clock" />
                {{ block.duration_minutes }} min
              </span>
              <span v-if="block.library_block_title" class="chip chip--library">
                <i class="pi pi-book" />
                {{ block.library_block_title }}
              </span>
            </div>

            <!-- Divider -->
            <div class="sheet-divider" />

            <!-- Rich content -->
            <div v-if="block.content" class="sheet-content prose" v-html="sanitized" />
            <p v-else class="sheet-no-content">Kein Inhalt hinterlegt.</p>

            <!-- Nextcloud link -->
            <a
              v-if="block.nextcloud_folder_url"
              :href="block.nextcloud_folder_url"
              target="_blank"
              rel="noopener noreferrer"
              class="nextcloud-link"
            >
              <i class="pi pi-cloud" />
              Nextcloud-Ordner öffnen
              <i class="pi pi-external-link" style="font-size: 0.7rem;" />
            </a>

            <!-- Media / Images -->
            <template v-if="loading">
              <div class="media-loading">
                <i class="pi pi-spin pi-spinner" />
                <span>Lade Medien…</span>
              </div>
            </template>

            <template v-else-if="media.length > 0">
              <div class="sheet-divider" />
              <div class="media-section">
                <h3 class="media-title">
                  <i class="pi pi-images" />
                  Bilder ({{ media.length }})
                </h3>
                <div class="media-grid">
                  <button
                    v-for="(item, idx) in media"
                    :key="item.id"
                    class="media-thumb-btn"
                    @click="openLightbox(idx)"
                  >
                    <img
                      :src="item.url"
                      :alt="item.original_filename"
                      class="media-thumb"
                      loading="lazy"
                    />
                  </button>
                </div>
              </div>
            </template>

            <!-- bottom safe-area spacer -->
            <div class="sheet-bottom-spacer" />
          </div>
        </div>
      </div>
    </Transition>

    <!-- Lightbox -->
    <Transition name="fade">
      <div v-if="lightboxIdx !== null" class="lightbox" @click.self="lightboxIdx = null">
        <button class="lightbox-close" @click="lightboxIdx = null" aria-label="Schließen">
          <i class="pi pi-times" />
        </button>
        <button
          v-if="lightboxIdx > 0"
          class="lightbox-nav lightbox-nav--prev"
          @click.stop="lightboxIdx = (lightboxIdx ?? 0) - 1"
          aria-label="Vorheriges Bild"
        >
          <i class="pi pi-chevron-left" />
        </button>
        <img
          v-if="lightboxIdx !== null"
          :src="media[lightboxIdx]?.url"
          :alt="media[lightboxIdx]?.original_filename"
          class="lightbox-img"
        />
        <button
          v-if="lightboxIdx < media.length - 1"
          class="lightbox-nav lightbox-nav--next"
          @click.stop="lightboxIdx = (lightboxIdx ?? 0) + 1"
          aria-label="Nächstes Bild"
        >
          <i class="pi pi-chevron-right" />
        </button>
        <div class="lightbox-caption">
          {{ media[lightboxIdx]?.original_filename }} ({{ (lightboxIdx ?? 0) + 1 }} / {{ media.length }})
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { trainingBlocksApi } from '@/api/training'
import type { PlannerBlock, TrainingMedia } from '@/types/training'

interface Props {
  block: PlannerBlock | null
  sessionStartMin: number
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()

const loading = ref(false)
const media = ref<TrainingMedia[]>([])
const lightboxIdx = ref<number | null>(null)

// ── Load media when sheet opens ──────────────────────────────────────────────
watch(
  () => props.block,
  async (b) => {
    media.value = []
    lightboxIdx.value = null
    if (!b) return
    // Block already carries `.media` from the list response if the backend
    // serialises it; use it immediately and silently refresh via the dedicated endpoint.
    if (b.media?.length) media.value = b.media
    loading.value = true
    try {
      const res = await trainingBlocksApi.listMedia(b.id)
      media.value = res.data
    } catch {
      // media pre-populated from block.media is still shown
    } finally {
      loading.value = false
    }
  },
)

// ── Time helpers ─────────────────────────────────────────────────────────────
function absMinToTime(abs: number): string {
  const hh = Math.floor(abs / 60) % 24
  const mm = abs % 60
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

const startTime = computed(() =>
  props.block ? absMinToTime(props.sessionStartMin + props.block.start_offset_minutes) : '',
)
const endTime = computed(() =>
  props.block
    ? absMinToTime(props.sessionStartMin + props.block.start_offset_minutes + props.block.duration_minutes)
    : '',
)

// ── Content sanitization ─────────────────────────────────────────────────────
const sanitized = computed(() => {
  const html = props.block?.content ?? ''
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/\s(on\w+)=["'][^"']*["']/gi, '')
    .replace(/\s(on\w+)=[^\s>]*/gi, '')
    .replace(/href\s*=\s*["']?\s*javascript:/gi, 'href="about:blank"')
})

// ── Lightbox ─────────────────────────────────────────────────────────────────
function openLightbox(idx: number) {
  lightboxIdx.value = idx
}
</script>

<style scoped>
/* ── Backdrop ─────────────────────────────────────────────────────────────── */
.sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}

/* ── Sheet panel ──────────────────────────────────────────────────────────── */
.sheet {
  width: 100%;
  max-height: 92svh;
  background: var(--p-content-background);
  border-radius: 16px 16px 0 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.18);
}

/* ── Handle bar ───────────────────────────────────────────────────────────── */
.sheet-handle-row {
  display: flex;
  justify-content: center;
  padding: 0.6rem 0 0.25rem;
  cursor: pointer;
  flex-shrink: 0;
}

.sheet-handle {
  width: 40px;
  height: 4px;
  background: var(--p-content-border-color);
  border-radius: 99px;
}

/* ── Scroll container ─────────────────────────────────────────────────────── */
.sheet-scroll {
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  flex: 1;
  padding: 0 1.25rem;
}

/* ── Header ───────────────────────────────────────────────────────────────── */
.sheet-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding-top: 0.25rem;
  padding-bottom: 0.5rem;
}

.sheet-header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.sheet-time-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--p-primary-color);
  font-variant-numeric: tabular-nums;
}

.sheet-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 700;
  line-height: 1.3;
}

.sheet-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: var(--p-content-border-color);
  color: var(--p-text-muted-color);
  cursor: pointer;
  flex-shrink: 0;
  font-size: 0.85rem;
  -webkit-tap-highlight-color: transparent;
  transition: background 0.1s;
}

.sheet-close:active {
  background: color-mix(in srgb, var(--p-content-border-color) 70%, var(--p-primary-color));
}

/* ── Chips ────────────────────────────────────────────────────────────────── */
.sheet-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding-bottom: 0.75rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 99px;
}

.chip .pi { font-size: 0.7rem; }

.chip--duration {
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
}

.chip--library {
  background: color-mix(in srgb, var(--p-text-muted-color) 12%, transparent);
  color: var(--p-text-muted-color);
}

/* ── Divider ──────────────────────────────────────────────────────────────── */
.sheet-divider {
  height: 1px;
  background: var(--p-content-border-color);
  margin: 0.75rem 0;
}

/* ── Rich text content ────────────────────────────────────────────────────── */
.sheet-content {
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--p-text-color);
  padding-bottom: 0.5rem;
  overflow-wrap: break-word;
}

/* Prose-style resets for TipTap output */
.sheet-content :deep(h1),
.sheet-content :deep(h2),
.sheet-content :deep(h3) {
  font-weight: 700;
  margin-top: 1em;
  margin-bottom: 0.4em;
  line-height: 1.3;
}
.sheet-content :deep(h1) { font-size: 1.2rem; }
.sheet-content :deep(h2) { font-size: 1.05rem; }
.sheet-content :deep(h3) { font-size: 0.95rem; }

.sheet-content :deep(p) { margin-top: 0; margin-bottom: 0.6em; }
.sheet-content :deep(p:last-child) { margin-bottom: 0; }

.sheet-content :deep(ul),
.sheet-content :deep(ol) {
  padding-left: 1.4rem;
  margin-bottom: 0.6em;
}
.sheet-content :deep(li) { margin-bottom: 0.2em; }

.sheet-content :deep(strong) { font-weight: 700; }
.sheet-content :deep(em) { font-style: italic; }
.sheet-content :deep(u) { text-decoration: underline; }

.sheet-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 0.5em 0;
}

.sheet-content :deep(a) {
  color: var(--p-primary-color);
  word-break: break-all;
}

.sheet-no-content {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  font-style: italic;
  margin: 0 0 0.5rem;
}

/* ── Nextcloud link ───────────────────────────────────────────────────────── */
.nextcloud-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--p-primary-color);
  text-decoration: none;
  padding: 0.5rem 0.85rem;
  border: 1px solid var(--p-primary-color);
  border-radius: 8px;
  margin-bottom: 0.75rem;
  -webkit-tap-highlight-color: transparent;
}

/* ── Media section ────────────────────────────────────────────────────────── */
.media-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  padding: 0.75rem 0;
}

.media-section { padding-bottom: 0.5rem; }

.media-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  font-weight: 600;
  margin: 0 0 0.6rem;
  color: var(--p-text-color);
}

.media-title .pi { font-size: 0.85rem; color: var(--p-text-muted-color); }

.media-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.media-thumb-btn {
  padding: 0;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  background: var(--p-content-border-color);
  aspect-ratio: 1 / 1;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.1s;
}
.media-thumb-btn:active { opacity: 0.75; }

.media-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* ── Bottom spacer ────────────────────────────────────────────────────────── */
.sheet-bottom-spacer {
  height: max(1.5rem, env(safe-area-inset-bottom, 1rem));
}

/* ── Sheet slide transition ───────────────────────────────────────────────── */
.sheet-enter-active,
.sheet-leave-active { transition: opacity 0.22s ease; }
.sheet-enter-from,
.sheet-leave-to { opacity: 0; }
.sheet-enter-active .sheet,
.sheet-leave-active .sheet { transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1); }
.sheet-enter-from .sheet,
.sheet-leave-to .sheet { transform: translateY(100%); }

/* ── Lightbox ─────────────────────────────────────────────────────────────── */
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
}

.lightbox-img {
  max-width: 100%;
  max-height: 100svh;
  object-fit: contain;
  border-radius: 4px;
  padding: 3rem 4rem;
  box-sizing: border-box;
  pointer-events: none;
}

.lightbox-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  -webkit-tap-highlight-color: transparent;
}

.lightbox-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  -webkit-tap-highlight-color: transparent;
}
.lightbox-nav--prev { left: 0.75rem; }
.lightbox-nav--next { right: 0.75rem; }

.lightbox-caption {
  position: absolute;
  bottom: max(1.25rem, env(safe-area-inset-bottom, 1.25rem));
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.6);
  padding: 0 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Fade transition (lightbox) ───────────────────────────────────────────── */
.fade-enter-active,
.fade-leave-active { transition: opacity 0.18s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>
