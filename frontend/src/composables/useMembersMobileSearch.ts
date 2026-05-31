import { ref, computed, watch, nextTick } from 'vue'
import { useMobile } from '@/composables/useMobile'

export function useMembersMobileSearch() {
  const { isMobile } = useMobile()
  const mobileSearchActive = ref(false)
  const mobileSearchInputRef = ref<HTMLInputElement | null>(null)
  const originalBodyOverflow = ref<string | null>(null)

  const isMobileSearchMode = computed(() => isMobile.value && mobileSearchActive.value)

  function openMobileSearch() {
    if (!isMobile.value) return
    mobileSearchActive.value = true
    nextTick(() => {
      mobileSearchInputRef.value?.focus()
    })
  }

  function closeMobileSearch() {
    mobileSearchActive.value = false
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur()
    }
  }

  function onSearchFocus() {
    openMobileSearch()
  }

  watch(isMobileSearchMode, (enabled) => {
    if (enabled) {
      if (originalBodyOverflow.value === null) {
        originalBodyOverflow.value = document.body.style.overflow
      }
      document.body.style.overflow = 'hidden'
      nextTick(() => {
        mobileSearchInputRef.value?.focus()
      })
      return
    }

    if (originalBodyOverflow.value !== null) {
      document.body.style.overflow = originalBodyOverflow.value
      originalBodyOverflow.value = null
    }
  })

  watch(isMobile, (mobile) => {
    if (!mobile) {
      mobileSearchActive.value = false
    }
  })

  return {
    isMobile,
    isMobileSearchMode,
    mobileSearchInputRef,
    openMobileSearch,
    closeMobileSearch,
    onSearchFocus,
  }
}
