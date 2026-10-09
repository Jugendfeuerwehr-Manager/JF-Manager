<script setup lang="ts">
import { computed, ref } from 'vue'
import Popover from 'primevue/popover'
import { useInboxStore } from '@/stores/inbox'
import type { InboxEntry } from '@/api/inbox'
import { categoryLabel, relativeTime } from '@/utils/inbox'

const inbox = useInboxStore()
const popover = ref<InstanceType<typeof Popover> | null>(null)

const total = computed(() => inbox.counts.total)
const badge = computed(() => (total.value > 99 ? '99+' : String(total.value)))
const tasksText = computed(() => `${inbox.counts.open_tasks} ${inbox.counts.open_tasks === 1 ? 'offene Aufgabe' : 'offene Aufgaben'}`)
const noticesText = computed(() => `${inbox.counts.unread_notices} ${inbox.counts.unread_notices === 1 ? 'neuer Hinweis' : 'neue Hinweise'}`)

function toggle(event: Event) {
  popover.value?.toggle(event)
}
function onShow() {
  void inbox.fetchCounts()
  void inbox.fetchLatest()
}
function isOpenTask(entry: InboxEntry) { return entry.type === 'task' && entry.task_state === 'open' }
function choose(entry: InboxEntry) {
  if (!entry.read) void inbox.markRead(entry.id).catch(() => { /* The entry stays unread; the link still works. */ })
  popover.value?.hide()
}
</script>

<template>
  <button
    type="button"
    class="bell"
    :aria-label="`Benachrichtigungen, ${total} offen`"
    aria-haspopup="dialog"
    @click="toggle"
  >
    <i class="pi pi-bell" aria-hidden="true"></i>
    <span v-if="total > 0" class="bell__badge" aria-hidden="true">{{ badge }}</span>
  </button>
  <Popover ref="popover" class="bell-popover" @show="onShow">
    <section class="bell-panel" aria-label="Benachrichtigungen">
      <h2 class="bell-panel__title">Benachrichtigungen</h2>
      <p class="bell-panel__summary">
        <span class="bell-panel__count">{{ tasksText }}</span>
        <span class="bell-panel__count">{{ noticesText }}</span>
      </p>
      <p v-if="inbox.latestError" class="bell-panel__error" role="alert">{{ inbox.latestError }}</p>
      <p v-else-if="!inbox.latest.length && !inbox.latestLoading" class="bell-panel__empty">Keine neuen Benachrichtigungen</p>
      <ul v-else class="bell-list">
        <li v-for="entry in inbox.latest" :key="entry.id">
          <router-link :to="entry.link || '/eingang'" class="bell-item" :class="{ 'bell-item--unread': !entry.read }" @click="choose(entry)">
            <span class="bell-item__text">
              <span class="bell-item__title">{{ entry.title }}</span>
              <span class="bell-item__meta">
                {{ isOpenTask(entry) ? 'Aufgabe · ' : '' }}{{ categoryLabel(entry.category) }} · {{ relativeTime(entry.updated_at) }}
              </span>
            </span>
            <span v-if="!entry.read" class="bell-item__new">Neu</span>
          </router-link>
        </li>
      </ul>
      <router-link to="/eingang" class="bell-panel__all" @click="popover?.hide()">Alle im Eingang<i class="pi pi-arrow-right" aria-hidden="true"></i></router-link>
    </section>
  </Popover>
</template>

<style scoped>
.bell { position: relative; flex: none; width: var(--jf-touch-target, 44px); height: var(--jf-touch-target, 44px); display: inline-flex; align-items: center; justify-content: center; border-radius: 999px; border: 0; background: transparent; color: var(--jf-color-text); cursor: pointer; font-size: 1.15rem; }
.bell:hover { background: var(--surface-hover); }
.bell:focus-visible, .bell-item:focus-visible, .bell-panel__all:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.bell__badge { position: absolute; top: 2px; right: 0; min-width: 20px; height: 20px; padding: 0 5px; box-sizing: border-box; border-radius: 10px; background: var(--jf-color-primary); color: var(--jf-color-on-primary); font-size: var(--jf-text-xs); font-weight: var(--jf-weight-bold); display: flex; align-items: center; justify-content: center; }
.bell-panel { width: min(360px, calc(100vw - 2 * var(--jf-space-2))); display: flex; flex-direction: column; gap: var(--jf-space-1); }
.bell-panel__title { margin: 0; font-size: var(--jf-text-md); font-weight: var(--jf-weight-bold); }
.bell-panel__summary { margin: 0; display: flex; flex-wrap: wrap; gap: var(--jf-space-1) var(--jf-space-2); font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); }
.bell-panel__empty, .bell-panel__error { margin: 0; padding: var(--jf-space-1) 0; color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.bell-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.bell-item { min-height: var(--jf-touch-target, 44px); display: flex; align-items: center; gap: var(--jf-space-1-5); padding: var(--jf-space-1) var(--jf-space-1-5); box-sizing: border-box; border-radius: var(--jf-radius-md); border: 1px solid var(--jf-color-border); color: var(--jf-color-text); text-decoration: none; }
.bell-item:hover { background: var(--surface-hover); }
.bell-item--unread { border-color: var(--jf-color-primary); }
.bell-item__text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.bell-item__title { font-weight: var(--jf-weight-semibold); overflow-wrap: anywhere; }
.bell-item__meta { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.bell-item__new { flex: none; padding: 0 var(--jf-space-1); border-radius: 999px; background: var(--jf-color-selected); color: var(--jf-color-selected-text); font-size: var(--jf-text-xs); font-weight: var(--jf-weight-bold); }
.bell-panel__all { min-height: var(--jf-touch-target, 44px); display: inline-flex; align-items: center; justify-content: center; gap: var(--jf-space-1); color: var(--jf-color-primary); font-weight: var(--jf-weight-semibold); text-decoration: none; }
</style>
