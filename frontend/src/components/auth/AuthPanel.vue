<template>
  <main class="auth-page">
    <section class="auth-panel" :aria-labelledby="headingId">
      <span class="auth-panel__icon" aria-hidden="true"><i :class="icon"></i></span>
      <h1 :id="headingId">{{ title }}</h1>
      <p v-if="description" class="auth-panel__description">{{ description }}</p>
      <slot />
    </section>
  </main>
</template>

<script setup lang="ts">
/** Centred panel for the public account pages (password reset), styled like the login form. */
interface Props {
  title: string
  description?: string
  icon?: string
  headingId?: string
}

withDefaults(defineProps<Props>(), { description: '', icon: 'pi pi-key', headingId: 'auth-heading' })
</script>

<style scoped>
.auth-page {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: var(--jf-space-4) var(--jf-space-2);
  background: var(--jf-color-ground);
  color: var(--jf-color-text);
}

.auth-panel {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding: var(--jf-space-4);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg, 12px);
  box-shadow: var(--jf-shadow-md);
}

.auth-panel__icon {
  display: grid;
  place-items: center;
  width: var(--jf-touch-target);
  height: var(--jf-touch-target);
  border-radius: var(--jf-radius-md, 10px);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
  font-size: 1.25rem;
}

h1 {
  margin: 0;
  font-size: 1.6rem;
  letter-spacing: -0.02em;
}

.auth-panel__description {
  margin: 0 0 var(--jf-space-1);
  color: var(--jf-color-text-muted);
  line-height: 1.6;
}

.auth-panel :deep(form) {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.auth-panel :deep(.field) {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
}

.auth-panel :deep(.field label) {
  font-weight: 600;
  font-size: 0.9rem;
}

.auth-panel :deep(.p-inputtext),
.auth-panel :deep(.p-password) {
  width: 100%;
}

.auth-panel :deep(input),
.auth-panel :deep(.p-button) {
  min-height: var(--jf-touch-target);
}

.auth-panel :deep(.auth-link) {
  align-self: center;
  color: var(--jf-color-primary);
  text-decoration: underline;
  text-underline-offset: 4px;
  min-height: var(--jf-touch-target);
  display: inline-flex;
  align-items: center;
}
</style>
