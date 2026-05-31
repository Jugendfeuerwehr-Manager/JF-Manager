import { ref, computed } from 'vue'
import { membersApi } from '@/api/members'
import type { MemberStats } from '@/types/members'

export function useMembersStats() {
  const statsExpanded = ref(false)
  const statsLoading = ref(false)
  const stats = ref<MemberStats | null>(null)

  const genderStats = computed(() => {
    if (!stats.value) return []
    const g = stats.value.gender
    return [
      { label: 'Männlich', value: g?.male ?? 0, color: '#4facfe' },
      { label: 'Weiblich', value: g?.female ?? 0, color: '#f093fb' },
      { label: 'Divers', value: g?.diverse ?? 0, color: '#43e97b' },
      { label: 'Unbekannt', value: g?.unknown ?? 0, color: '#aaaaaa' },
    ].filter((e) => e.value > 0)
  })

  async function loadStats() {
    if (stats.value) return
    statsLoading.value = true
    try {
      const response = await membersApi.getStatistics()
      stats.value = response.data
    } catch {
      stats.value = null
    } finally {
      statsLoading.value = false
    }
  }

  async function toggleStats() {
    statsExpanded.value = !statsExpanded.value
    if (statsExpanded.value && !stats.value) {
      await loadStats()
    }
  }

  return {
    statsExpanded,
    statsLoading,
    stats,
    genderStats,
    loadStats,
    toggleStats,
  }
}
