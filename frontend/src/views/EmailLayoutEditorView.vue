<template>
  <div class="email-layout-page">
    <EmailLayoutEditor :key="layoutType" :layout-type="layoutType" />
  </div>
</template>

<script setup lang="ts">
import EmailLayoutEditor from '@/components/settings/organisms/EmailLayoutEditor.vue'

defineProps<{ layoutType: string }>()
</script>

<style scoped>
.email-layout-page {
  /* Fills the content area next to the navigation; the route is a full-width workspace. */
  height: calc(100dvh - var(--topbar-height, 64px));
  display: flex;
  flex-direction: column;
}

@media (max-width: 1023px) {
  .email-layout-page { height: auto; }
}
</style>
