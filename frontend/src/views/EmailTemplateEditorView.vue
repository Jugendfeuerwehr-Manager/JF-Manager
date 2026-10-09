<template>
  <div class="email-template-page">
    <EmailTemplateEditor :key="templateId ?? 'new'" :template-id="templateId" />
  </div>
</template>

<script setup lang="ts">
import EmailTemplateEditor from '@/components/settings/organisms/EmailTemplateEditor.vue'

defineProps<{ templateId: number | null }>()
</script>

<style scoped>
.email-template-page {
  /* Fills the content area next to the navigation; the route is a full-width workspace. */
  height: calc(100dvh - var(--topbar-height, 64px));
  display: flex;
  flex-direction: column;
}

@media (max-width: 1023px) {
  .email-template-page { height: auto; }
}
</style>
