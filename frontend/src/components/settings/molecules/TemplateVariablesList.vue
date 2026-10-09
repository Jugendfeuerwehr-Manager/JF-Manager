<template>
  <div class="template-variables">
    <Message v-if="variables?.warning" severity="warn" :closable="false">
      {{ variables.warning }}
    </Message>

    <ul v-if="variables && variables.variables.length > 0" class="template-variables__list">
      <li v-for="variable in variables.variables" :key="variable.name" class="template-variables__item">
        <code class="template-variables__name">{{ formatVariableName(variable.name) }}</code>
        <p class="template-variables__description">
          <span class="template-variables__type">{{ variable.type }}</span>
          {{ variable.description }}
        </p>
        <details v-if="variable.properties" class="template-variables__properties">
          <summary>{{ variable.properties.length }} Eigenschaften</summary>
          <ul>
            <li v-for="prop in variable.properties" :key="prop">
              <code>{{ formatVariableProperty(variable.name, prop) }}</code>
            </li>
          </ul>
        </details>
      </li>
    </ul>

    <p v-else-if="!variables" class="template-variables__empty">Wählen Sie einen Vorlagentyp aus.</p>
    <p v-else class="template-variables__empty">Für diesen Vorlagentyp sind keine Variablen definiert.</p>
  </div>
</template>

<script setup lang="ts">
import Message from 'primevue/message'
import type { TemplateVariables } from '@/types/email-templates'

interface Props {
  variables: TemplateVariables | null
}

defineProps<Props>()

function formatVariableName(name: string): string {
  return `{{ ${name} }}`
}

function formatVariableProperty(name: string, prop: string): string {
  return `{{ ${name}.${prop} }}`
}
</script>

<style scoped>
.template-variables {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}

.template-variables__list {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.template-variables__item {
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
}

code {
  font-family: var(--jf-font-mono);
  overflow-wrap: anywhere;
  user-select: all;
}

.template-variables__name {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
}

.template-variables__description {
  margin: var(--jf-space-0-5) 0 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text);
}

.template-variables__type {
  margin-right: var(--jf-space-0-5);
  padding: 0 6px;
  border-radius: var(--jf-radius-sm);
  background: var(--jf-color-ground);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text-muted);
}

.template-variables__properties {
  margin-top: var(--jf-space-1);
  font-size: var(--jf-text-sm);
}

.template-variables__properties summary {
  min-height: 32px;
  display: flex;
  align-items: center;
  cursor: pointer;
  color: var(--jf-color-text-muted);
  font-weight: var(--jf-weight-semibold);
}

.template-variables__properties ul {
  margin: var(--jf-space-0-5) 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.template-variables__properties code { font-size: var(--jf-text-xs); }

.template-variables__empty {
  margin: 0;
  padding: var(--jf-space-3) var(--jf-space-2);
  text-align: center;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}
</style>
