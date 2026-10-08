<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PortalSheet from '@/components/portal/PortalSheet.vue'
import { usePortalStore } from '@/stores/portal'
import { relativeTime } from '@/utils/inbox'
import type { PortalNotice } from '@/api/portal'

const portal = usePortalStore()
const router = useRouter()
const open = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

function refresh() {
  if (document.visibilityState === 'hidden') return
  void portal.loadNotices()
}
async function choose(notice: PortalNotice) {
  void portal.markNoticeRead(notice.id)
  open.value = false
  if (notice.link) await router.push(notice.link)
}

onMounted(() => {
  void portal.loadNotices()
  timer = setInterval(refresh, 60_000)
  document.addEventListener('visibilitychange', refresh)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  document.removeEventListener('visibilitychange', refresh)
})
</script>

<template>
  <button type="button" class="bell" :aria-label="`Hinweise, ${portal.unreadNotices} neu`" aria-haspopup="dialog" @click="open = true">
    <i class="pi pi-bell" aria-hidden="true"></i>
    <span v-if="portal.unreadNotices > 0" class="badge" aria-hidden="true">{{ portal.unreadNotices > 9 ? '9+' : portal.unreadNotices }}</span>
  </button>
  <PortalSheet v-if="open" title="Hinweise" title-id="notice-sheet-title" @close="open = false">
    <p v-if="!portal.notices.length" class="empty">Keine Hinweise</p>
    <ul v-else class="list">
      <li v-for="notice in portal.notices" :key="notice.id">
        <button type="button" class="item" :class="{ unread: !notice.read }" @click="choose(notice)">
          <span class="dot" aria-hidden="true"></span>
          <span class="text">
            <span class="title">{{ notice.title }}</span>
            <span class="time">{{ relativeTime(notice.updated_at) }}<template v-if="!notice.read"> · neu</template></span>
          </span>
          <i v-if="notice.link" class="pi pi-chevron-right" aria-hidden="true"></i>
        </button>
      </li>
    </ul>
  </PortalSheet>
</template>

<style scoped>
.bell { position: relative; flex: none; width: 44px; height: 44px; display: inline-flex; align-items: center; justify-content: center; border-radius: 12px; border: 1px solid var(--p-content-border-color); background: var(--p-content-background); color: var(--p-text-color); cursor: pointer; font-size: 18px; }
.bell:focus-visible, .item:focus-visible { outline: 2px solid var(--p-primary-color); outline-offset: 2px; }
.badge { position: absolute; top: -6px; right: -6px; min-width: 20px; height: 20px; padding: 0 5px; box-sizing: border-box; border-radius: 10px; background: var(--p-primary-color); color: var(--p-primary-contrast-color); font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.empty { margin: 0; padding: 16px 0; text-align: center; color: var(--p-text-muted-color); }
.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.item { width: 100%; min-height: 56px; display: flex; align-items: center; gap: 12px; padding: 10px 12px; box-sizing: border-box; text-align: left; border-radius: 12px; border: 1px solid var(--p-content-border-color); background: var(--p-content-background); color: var(--p-text-color); cursor: pointer; font: inherit; }
.item.unread { border-color: var(--p-primary-color); }
.dot { flex: none; width: 8px; height: 8px; border-radius: 50%; background: transparent; }
.unread .dot { background: var(--p-primary-color); }
.text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.title { font-weight: 600; overflow-wrap: anywhere; }
.unread .title { font-weight: 700; }
.time { font-size: 13px; color: var(--p-text-muted-color); }
</style>
